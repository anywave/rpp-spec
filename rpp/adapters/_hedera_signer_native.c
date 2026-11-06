#define PY_SSIZE_T_CLEAN
#include <Python.h>

#if defined(Py_GIL_DISABLED) && Py_GIL_DISABLED
#error "The experimental Hedera signer requires GIL-enabled CPython"
#endif

/* No Python callback/destructor or module-owned lifetime is needed here. */
static const char signer_name[] = "rpp.hedera.signer.v1";
static char closed_marker;

static void
sanitize_signing_error(void)
{
    PyObject *error_type = NULL, *error_value = NULL, *error_traceback = NULL;
    PyObject *replacement = NULL, *code = NULL, *asyncio_module = NULL;
    PyObject *cancelled_error = NULL;
    PyErr_Fetch(&error_type, &error_value, &error_traceback);
    PyErr_NormalizeException(&error_type, &error_value, &error_traceback);
    if (PyErr_Occurred()) {
        PyErr_Clear();
    }
    if (error_type != NULL &&
            PyErr_GivenExceptionMatches(error_type, PyExc_SystemExit)) {
        replacement = PyExc_SystemExit;
        if (error_value != NULL && PyObject_TypeCheck(
                error_value, (PyTypeObject *)PyExc_SystemExit)) {
            PyObject *original_code = ((PySystemExitObject *)error_value)->code;
            if (original_code == Py_None ||
                    (original_code != NULL && PyLong_CheckExact(original_code))) {
                code = Py_NewRef(original_code);
            }
        }
    }
    else if (error_type != NULL &&
            PyErr_GivenExceptionMatches(error_type, PyExc_KeyboardInterrupt)) {
        replacement = PyExc_KeyboardInterrupt;
    }
    else if (error_type != NULL &&
            PyErr_GivenExceptionMatches(error_type, PyExc_GeneratorExit)) {
        replacement = PyExc_GeneratorExit;
    }
    else {
        asyncio_module = PyImport_ImportModule("asyncio.exceptions");
        if (asyncio_module != NULL) {
            cancelled_error = PyObject_GetAttrString(asyncio_module, "CancelledError");
        }
        if (cancelled_error != NULL && error_type != NULL &&
                PyErr_GivenExceptionMatches(error_type, cancelled_error)) {
            replacement = cancelled_error;
        }
        PyErr_Clear();
    }
    /* Discard the entire SDK error graph before publishing a replacement. */
    Py_XDECREF(error_type);
    Py_XDECREF(error_value);
    Py_XDECREF(error_traceback);
    Py_XDECREF(asyncio_module);
    PyErr_Clear();
    if (replacement == PyExc_SystemExit) {
        PyErr_SetObject(replacement, code == NULL ? Py_None : code);
    }
    else if (replacement != NULL) {
        PyErr_SetNone(replacement);
    }
    else {
        PyErr_SetString(PyExc_RuntimeError, "Hedera signing failed");
    }
    Py_XDECREF(code);
    Py_XDECREF(cancelled_error);
}

static int
require_main_interpreter(void)
{
    if (PyThreadState_GetInterpreter(PyThreadState_Get()) !=
            PyInterpreterState_Main()) {
        PyErr_SetString(PyExc_RuntimeError,
                        "Experimental Hedera signing requires the main interpreter");
        return -1;
    }
    return 0;
}

static PyObject *
get_operation(PyObject *capsule)
{
    void *pointer;
    if (!PyCapsule_IsValid(capsule, signer_name)) {
        PyErr_SetString(PyExc_TypeError, "Invalid Hedera signer handle");
        return NULL;
    }
    pointer = PyCapsule_GetPointer(capsule, signer_name);
    if (pointer == (void *)&closed_marker) {
        PyErr_SetString(PyExc_RuntimeError, "Hedera signer is closed");
        return NULL;
    }
    return (PyObject *)pointer;  /* Borrowed; every public entry holds the GIL. */
}

static int
release_operation(PyObject *capsule)
{
    PyObject *operation;
    void *pointer;
    if (!PyCapsule_IsValid(capsule, signer_name)) {
        PyErr_SetString(PyExc_TypeError, "Invalid Hedera signer handle");
        return -1;
    }
    pointer = PyCapsule_GetPointer(capsule, signer_name);
    if (pointer == (void *)&closed_marker) {
        return 0;
    }
    operation = (PyObject *)pointer;
    /* One native transition: saved handles close before the owned ref drops. */
    if (PyCapsule_SetPointer(capsule, (void *)&closed_marker) < 0) {
        return -1;
    }
    Py_DECREF(operation);
    return 0;
}

static void
signer_destructor(PyObject *capsule)
{
    PyObject *error_type, *error_value, *error_traceback;
    PyErr_Fetch(&error_type, &error_value, &error_traceback);
    if (release_operation(capsule) < 0) {
        PyErr_Clear();
    }
    PyErr_Restore(error_type, error_value, error_traceback);
}

static PyObject *
signer_new(PyObject *module, PyObject *operation)
{
    PyObject *capsule;
    (void)module;
    if (require_main_interpreter() < 0) {
        return NULL;
    }
    if (!PyCallable_Check(operation)) {
        PyErr_SetString(PyExc_TypeError, "Hedera signing operation must be callable");
        return NULL;
    }
    /* No Python opcode/signal dispatch can separate this pin from its owner. */
    Py_INCREF(operation);
    capsule = PyCapsule_New(operation, signer_name, signer_destructor);
    if (capsule == NULL) {
        Py_DECREF(operation);
    }
    return capsule;
}

static PyObject *
signer_release(PyObject *module, PyObject *capsule)
{
    (void)module;
    if (require_main_interpreter() < 0) {
        return NULL;
    }
    if (release_operation(capsule) < 0) {
        return NULL;
    }
    Py_RETURN_NONE;
}

static PyObject *
signer_closed(PyObject *module, PyObject *capsule)
{
    (void)module;
    if (require_main_interpreter() < 0) {
        return NULL;
    }
    if (!PyCapsule_IsValid(capsule, signer_name)) {
        PyErr_SetString(PyExc_TypeError, "Invalid Hedera signer handle");
        return NULL;
    }
    return PyBool_FromLong(PyCapsule_GetPointer(capsule, signer_name) ==
                           (void *)&closed_marker);
}

static PyObject *
signer_invoke(PyObject *module, PyObject *args)
{
    PyObject *capsule, *payload, *operation, *result;
    (void)module;
    if (require_main_interpreter() < 0) {
        return NULL;
    }
    if (!PyArg_ParseTuple(args, "OO:invoke", &capsule, &payload)) {
        return NULL;
    }
    operation = get_operation(capsule);
    if (operation == NULL) {
        return NULL;
    }
    /* release() may run while Python signing code releases the GIL. */
    Py_INCREF(operation);
    result = PyObject_CallOneArg(operation, payload);
    Py_DECREF(operation);
    if (result == NULL) {
        sanitize_signing_error();
        return NULL;
    }
    if (!PyBytes_CheckExact(result)) {
        Py_DECREF(result);
        PyErr_SetString(PyExc_TypeError, "Hedera signer returned an invalid signature");
        return NULL;
    }
    return result;
}

static PyMethodDef signer_methods[] = {
    {"new", signer_new, METH_O, "Create an opaque native signing-operation owner."},
    {"release", signer_release, METH_O, "Close a signing-operation owner idempotently."},
    {"closed", signer_closed, METH_O, "Check whether an owner has been closed."},
    {"invoke", signer_invoke, METH_VARARGS, "Invoke signing without exposing its operation."},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef signer_module = {
    PyModuleDef_HEAD_INIT,
    "_hedera_signer_native",
    "Experimental opaque signing ownership for GIL-enabled CPython.",
    -1,
    signer_methods,
    NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit__hedera_signer_native(void)
{
    if (PyThreadState_GetInterpreter(PyThreadState_Get()) !=
            PyInterpreterState_Main()) {
        PyErr_SetString(PyExc_ImportError,
                        "Experimental Hedera signing requires the main interpreter");
        return NULL;
    }
    return PyModule_Create(&signer_module);
}
