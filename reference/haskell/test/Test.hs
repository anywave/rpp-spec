-- | Test suite for RPP Address reference implementation
module Main where

import RPPAddress
import System.Exit (exitSuccess, exitFailure)

-- =============================================================================
-- Test Vectors from spec/test_vectors.json
-- =============================================================================

-- | Test minimum address
testMinAddress :: Bool
testMinAddress = decode 0x00000000 == (0, 0, 0, 0)

-- | Test maximum address
testMaxAddress :: Bool
testMaxAddress = decode 0x0FFFFFFF == (3, 511, 511, 255)

-- | Test shell isolation
testShellOnly :: Bool
testShellOnly = decode 0x0C000000 == (3, 0, 0, 0)

-- | Test theta isolation
testThetaOnly :: Bool
testThetaOnly = decode 0x03FE0000 == (0, 511, 0, 0)

-- | Test phi isolation
testPhiOnly :: Bool
testPhiOnly = decode 0x0001FF00 == (0, 0, 511, 0)

-- | Test harmonic isolation
testHarmonicOnly :: Bool
testHarmonicOnly = decode 0x000000FF == (0, 0, 0, 255)

-- =============================================================================
-- Roundtrip Tests
-- =============================================================================

-- | Test roundtrip for various addresses
testRoundtrip :: Bool
testRoundtrip = all checkRoundtrip testCases
  where
    testCases =
      [ (0, 0, 0, 0)
      , (3, 511, 511, 255)
      , (0, 45, 128, 64)
      , (1, 96, 192, 128)
      , (2, 160, 96, 255)
      , (3, 352, 64, 1)
      , (0, 256, 256, 128)
      , (1, 100, 200, 100)
      ]
    checkRoundtrip (s, t, p, h) =
      decode (encode s t p h) == (s, t, p, h)

-- =============================================================================
-- Semantic Interpretation Tests
-- =============================================================================

-- | Test sector names
testSectorNames :: Bool
testSectorNames = all checkSector sectorTests
  where
    sectorTests =
      [ (32,  "gene")
      , (96,  "memory")
      , (160, "witness")
      , (224, "dream")
      , (288, "bridge")
      , (352, "guardian")
      , (416, "emergence")
      , (480, "meta")
      ]
    checkSector (t, expected) =
      sectorName (fromComponents 0 t 256 128) == expected

-- | Test grounding levels
testGroundingLevels :: Bool
testGroundingLevels = all checkLevel levelTests
  where
    levelTests =
      [ (64,  "grounded")
      , (192, "transitional")
      , (320, "abstract")
      , (448, "ethereal")
      ]
    checkLevel (p, expected) =
      groundingLevel (fromComponents 0 256 p 128) == expected

-- | Test shell names
testShellNames :: Bool
testShellNames = all checkShell shellTests
  where
    shellTests =
      [ (0, "hot")
      , (1, "warm")
      , (2, "cold")
      , (3, "frozen")
      ]
    checkShell (s, expected) =
      shellName (fromComponents s 256 256 128) == expected

-- =============================================================================
-- Conversion Tests
-- =============================================================================

-- | Test degrees to theta conversion
testDegreesToTheta :: Bool
testDegreesToTheta = all checkConv convTests
  where
    convTests =
      [ (0,   0)
      , (180, 256)
      , (90,  128)
      , (270, 384)
      ]
    checkConv (deg, expected) =
      degreesToTheta deg == expected

-- | Test latitude to phi conversion
testLatitudeToPhi :: Bool
testLatitudeToPhi = all checkConv convTests
  where
    convTests =
      [ (-90, 0)
      , (0,   256)
      , (90,  511)  -- Note: 512 would overflow
      ]
    checkConv (lat, expected) =
      latitudeToPhi lat == expected

-- =============================================================================
-- Main Test Runner
-- =============================================================================

main :: IO ()
main = do
  putStrLn "RPP Address Test Suite"
  putStrLn "======================"
  putStrLn ""

  let results =
        [ ("Min address",      testMinAddress)
        , ("Max address",      testMaxAddress)
        , ("Shell isolation",  testShellOnly)
        , ("Theta isolation",  testThetaOnly)
        , ("Phi isolation",    testPhiOnly)
        , ("Harmonic isolation", testHarmonicOnly)
        , ("Roundtrip",        testRoundtrip)
        , ("Sector names",     testSectorNames)
        , ("Grounding levels", testGroundingLevels)
        , ("Shell names",      testShellNames)
        , ("Degrees to theta", testDegreesToTheta)
        , ("Latitude to phi",  testLatitudeToPhi)
        ]

  mapM_ printResult results

  putStrLn ""
  let passed = length $ filter snd results
  let total = length results
  putStrLn $ show passed ++ "/" ++ show total ++ " tests passed"

  if all snd results
    then do
      putStrLn "All tests passed!"
      exitSuccess
    else do
      putStrLn "SOME TESTS FAILED!"
      exitFailure

  where
    printResult (name, result) =
      putStrLn $ (if result then "[PASS] " else "[FAIL] ") ++ name
