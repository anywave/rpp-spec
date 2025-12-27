{-|
Module      : RPPAddress
Description : RPP Reference Implementation in Haskell
Copyright   : (c) Alexander Liam Lennon, 2024
License     : Apache-2.0
Maintainer  : rpp-spec@example.org
Stability   : stable
Portability : portable

Reference implementation of RPP (Rotational Packet Protocol) address
encoding and decoding in pure Haskell.

= Address Format

28-bit address: @[Shell:2][Theta:9][Phi:9][Harmonic:8]@

* Shell (bits 27:26): Storage tier (0-3)
* Theta (bits 25:17): Angular position (0-511)
* Phi (bits 16:8): Elevation angle (0-511)
* Harmonic (bits 7:0): Resolution/mode (0-255)

= Usage

@
import RPPAddress

-- Encode an address
let addr = encode 0 45 128 64
-- addr = 0x005A040

-- Decode an address
let (shell, theta, phi, harmonic) = decode addr
-- (0, 45, 128, 64)

-- Create RPPAddress with semantic interpretation
let rppAddr = fromComponents 1 96 192 128
-- rppAddr.sectorName = "memory"
-- rppAddr.groundingLevel = "transitional"
@
-}

module RPPAddress
  ( -- * Core Types
    RPPAddress(..)
  , Shell
  , Theta
  , Phi
  , Harmonic
  , Address
    -- * Encoding/Decoding
  , encode
  , decode
  , fromComponents
  , fromRaw
    -- * Semantic Interpretation
  , sectorName
  , groundingLevel
  , shellName
    -- * Conversions
  , degreesToTheta
  , latitudeToPhi
  , toHex
    -- * Constants
  , maxAddress
  , shellMask
  , thetaMask
  , phiMask
  , harmonicMask
  ) where

import Data.Word (Word32)
import Data.Bits ((.&.), (.|.), shiftL, shiftR)
import Text.Printf (printf)

-- =============================================================================
-- Type Aliases
-- =============================================================================

-- | Shell: 2-bit storage tier (0-3)
type Shell = Int

-- | Theta: 9-bit angular position (0-511)
type Theta = Int

-- | Phi: 9-bit elevation angle (0-511)
type Phi = Int

-- | Harmonic: 8-bit resolution/mode (0-255)
type Harmonic = Int

-- | Address: 28-bit RPP address
type Address = Word32

-- =============================================================================
-- Constants
-- =============================================================================

-- | Maximum valid 28-bit address (0x0FFFFFFF)
maxAddress :: Address
maxAddress = 0x0FFFFFFF

-- | Shell field mask (bits 27:26)
shellMask :: Address
shellMask = 0x0C000000

-- | Theta field mask (bits 25:17)
thetaMask :: Address
thetaMask = 0x03FE0000

-- | Phi field mask (bits 16:8)
phiMask :: Address
phiMask = 0x0001FF00

-- | Harmonic field mask (bits 7:0)
harmonicMask :: Address
harmonicMask = 0x000000FF

-- =============================================================================
-- RPPAddress Data Type
-- =============================================================================

-- | RPP Address with decoded components and semantic interpretation
data RPPAddress = RPPAddress
  { raw      :: !Address    -- ^ Raw 28-bit address
  , shell    :: !Shell      -- ^ Storage tier (0-3)
  , theta    :: !Theta      -- ^ Angular position (0-511)
  , phi      :: !Phi        -- ^ Elevation angle (0-511)
  , harmonic :: !Harmonic   -- ^ Resolution/mode (0-255)
  } deriving (Eq)

instance Show RPPAddress where
  show addr = printf "RPPAddress(%s: shell=%d, theta=%d, phi=%d, harmonic=%d)"
    (toHex $ raw addr)
    (shell addr)
    (theta addr)
    (phi addr)
    (harmonic addr)

-- =============================================================================
-- Encoding Functions
-- =============================================================================

-- | Encode components into a 28-bit RPP address
--
-- >>> encode 0 45 128 64
-- 5939264
--
-- >>> toHex (encode 0 45 128 64)
-- "0x005A8040"
encode :: Shell -> Theta -> Phi -> Harmonic -> Address
encode s t p h
  | s < 0 || s > 3     = error $ "Shell out of range (0-3): " ++ show s
  | t < 0 || t > 511   = error $ "Theta out of range (0-511): " ++ show t
  | p < 0 || p > 511   = error $ "Phi out of range (0-511): " ++ show p
  | h < 0 || h > 255   = error $ "Harmonic out of range (0-255): " ++ show h
  | otherwise = fromIntegral $
      (s `shiftL` 26) .|.
      (t `shiftL` 17) .|.
      (p `shiftL` 8)  .|.
      h

-- | Decode a 28-bit RPP address into components
--
-- >>> decode 0x005A8040
-- (0, 45, 128, 64)
decode :: Address -> (Shell, Theta, Phi, Harmonic)
decode addr
  | addr > maxAddress = error $ "Address exceeds 28 bits: " ++ show addr
  | otherwise = (s, t, p, h)
  where
    addr' = fromIntegral addr :: Int
    s = (addr' `shiftR` 26) .&. 0x3
    t = (addr' `shiftR` 17) .&. 0x1FF
    p = (addr' `shiftR` 8)  .&. 0x1FF
    h = addr' .&. 0xFF

-- =============================================================================
-- RPPAddress Constructors
-- =============================================================================

-- | Create RPPAddress from components
--
-- >>> fromComponents 1 96 192 128
-- RPPAddress(0x04C0C080: shell=1, theta=96, phi=192, harmonic=128)
fromComponents :: Shell -> Theta -> Phi -> Harmonic -> RPPAddress
fromComponents s t p h = RPPAddress
  { raw      = encode s t p h
  , shell    = s
  , theta    = t
  , phi      = p
  , harmonic = h
  }

-- | Create RPPAddress from raw 28-bit address
--
-- >>> fromRaw 0x005A8040
-- RPPAddress(0x005A8040: shell=0, theta=45, phi=128, harmonic=64)
fromRaw :: Address -> RPPAddress
fromRaw addr = RPPAddress
  { raw      = addr
  , shell    = s
  , theta    = t
  , phi      = p
  , harmonic = h
  }
  where
    (s, t, p, h) = decode addr

-- =============================================================================
-- Semantic Interpretation
-- =============================================================================

-- | Sector boundaries for theta ranges
sectors :: [(Int, Int, String)]
sectors =
  [ (0,   64,  "gene")
  , (64,  128, "memory")
  , (128, 192, "witness")
  , (192, 256, "dream")
  , (256, 320, "bridge")
  , (320, 384, "guardian")
  , (384, 448, "emergence")
  , (448, 512, "meta")
  ]

-- | Get sector name from theta value
--
-- >>> sectorName (fromComponents 0 96 128 64)
-- "memory"
sectorName :: RPPAddress -> String
sectorName addr = findSector (theta addr) sectors
  where
    findSector _ [] = "unknown"
    findSector t ((lo, hi, name):rest)
      | t >= lo && t < hi = name
      | otherwise = findSector t rest

-- | Grounding level boundaries for phi ranges
groundingLevels :: [(Int, Int, String)]
groundingLevels =
  [ (0,   128, "grounded")
  , (128, 256, "transitional")
  , (256, 384, "abstract")
  , (384, 512, "ethereal")
  ]

-- | Get grounding level from phi value
--
-- >>> groundingLevel (fromComponents 0 45 192 64)
-- "transitional"
groundingLevel :: RPPAddress -> String
groundingLevel addr = findLevel (phi addr) groundingLevels
  where
    findLevel _ [] = "unknown"
    findLevel p ((lo, hi, level):rest)
      | p >= lo && p < hi = level
      | otherwise = findLevel p rest

-- | Shell names for storage tiers
shellNames :: [String]
shellNames = ["hot", "warm", "cold", "frozen"]

-- | Get shell name from shell value
--
-- >>> shellName (fromComponents 2 45 128 64)
-- "cold"
shellName :: RPPAddress -> String
shellName addr
  | s >= 0 && s < length shellNames = shellNames !! s
  | otherwise = "unknown"
  where s = shell addr

-- =============================================================================
-- Conversion Functions
-- =============================================================================

-- | Convert degrees (0-360) to theta (0-511)
--
-- >>> degreesToTheta 180
-- 256
degreesToTheta :: Double -> Theta
degreesToTheta deg = floor $ (deg / 360.0) * 512.0

-- | Convert latitude (-90 to +90) to phi (0-511)
--
-- >>> latitudeToPhi 0
-- 256
latitudeToPhi :: Double -> Phi
latitudeToPhi lat = floor $ ((lat + 90.0) / 180.0) * 512.0

-- | Convert address to hex string
--
-- >>> toHex 0x005A8040
-- "0x005A8040"
toHex :: Address -> String
toHex = printf "0x%08X"

-- =============================================================================
-- Test Vectors (for validation)
-- =============================================================================

-- | Test vector: minimum address
testMin :: Bool
testMin = decode 0x00000000 == (0, 0, 0, 0)

-- | Test vector: maximum address
testMax :: Bool
testMax = decode 0x0FFFFFFF == (3, 511, 511, 255)

-- | Test vector: roundtrip encoding
testRoundtrip :: Bool
testRoundtrip = all checkRoundtrip testCases
  where
    testCases = [(0,45,128,64), (1,96,192,128), (2,160,96,255), (3,352,64,1)]
    checkRoundtrip (s,t,p,h) = decode (encode s t p h) == (s,t,p,h)

-- | Run all tests
runTests :: IO ()
runTests = do
  putStrLn "RPP Address Tests"
  putStrLn "================="
  putStrLn $ "Test min address: " ++ show testMin
  putStrLn $ "Test max address: " ++ show testMax
  putStrLn $ "Test roundtrip:   " ++ show testRoundtrip
  putStrLn ""
  if testMin && testMax && testRoundtrip
    then putStrLn "All tests passed!"
    else putStrLn "SOME TESTS FAILED!"
