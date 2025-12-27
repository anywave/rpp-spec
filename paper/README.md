# RPP arXiv Paper

This directory contains the LaTeX source for the arXiv preprint submission.

## Files

- `main.tex` - Main LaTeX source file

## Building

```bash
# Using pdflatex
pdflatex main.tex
pdflatex main.tex  # Run twice for references

# Or using latexmk
latexmk -pdf main.tex
```

## arXiv Submission

### Category
- Primary: **cs.OS** (Operating Systems)
- Secondary: **cs.DC** (Distributed Computing), **cs.AR** (Hardware Architecture)

### Submission Checklist

1. [ ] Build PDF locally and verify formatting
2. [ ] Ensure all figures render correctly
3. [ ] Verify bibliography compiles
4. [ ] Create submission archive: `tar -cvf rpp-paper.tar main.tex`
5. [ ] Submit to arXiv (requires endorsement for cs.OS)

## Citation

After arXiv acceptance, the paper can be cited as:

```bibtex
@misc{lennon2024rpp,
  title={Rotational Packet Protocol (RPP): A Semantic Addressing Architecture for Consent-Aware Memory Systems},
  author={Lennon, Alexander Liam},
  year={2024},
  eprint={XXXX.XXXXX},
  archivePrefix={arXiv},
  primaryClass={cs.OS}
}
```

## License

CC BY 4.0
