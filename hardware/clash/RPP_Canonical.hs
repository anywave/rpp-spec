{-# LANGUAGE DataKinds #-}
{-# LANGUAGE TypeFamilies #-}
{-# LANGUAGE TypeOperators #-}
{-# LANGUAGE NoImplicitPrelude #-}
{-# LANGUAGE DeriveGeneric #-}
{-# LANGUAGE DeriveAnyClass #-}
{-# LANGUAGE RecordWildCards #-}
{-# LANGUAGE MultiParamTypeClasses #-}
{-# LANGUAGE FlexibleContexts #-}

{-|
Module      : RPP_Canonical
Description : Ra-Canonical v2.0 RPP FPGA Implementation
Copyright   : (c) Alexander Liam Lennon, 2025
License     : Apache-2.0

Clash implementation of the Ra-Canonical v2.0 Rotational Packet Protocol.

This module replaces the legacy 28-bit format with the semantic Ra-Canonical
32-bit address format based on the 27 Repitans.

Address Format (32 bits):
  [31:27] theta (5 bits)  - Repitan index 1-27
  [26:24] phi (3 bits)    - RAC access level 1-6
  [23:21] omega (3 bits)  - Omega tier 0-4
  [20:13] radius (8 bits) - Intensity scalar 0-255
  [12:0]  reserved (13 bits) - CRC or future use

Repository: https://github.com/anywave/rpp-spec

Hardware Targets:
- Xilinx 7-series (Artix-7, Kintex-7)
- Intel Cyclone V / Arria 10
- Lattice ECP5
- ESP32-S3 (via soft synthesis or C port)
- Helium/LoRaWAN IoT gateways

Usage:
  # Generate Verilog
  clash --verilog RPP_Canonical.hs

  # Generate VHDL
  clash --vhdl RPP_Canonical.hs
-}

module RPP_Canonical where

import Clash.Prelude
import Clash.Explicit.Testbench
import GHC.Generics (Generic)

-- =============================================================================
-- RA-CANONICAL ADDRESS FORMAT (32 bits)
-- =============================================================================

-- | Theta: Repitan index (1-27, 5 bits)
-- 27 Repitans map to 8 ThetaSectors
type Theta = Unsigned 5

-- | Phi: RAC access level (1-6, 3 bits)
-- RAC1 = highest sensitivity, RAC6 = lowest
type Phi = Unsigned 3

-- | Omega: Omega tier (0-4, 3 bits)
-- RED=0, OMEGA_MAJOR=1, GREEN=2, OMEGA_MINOR=3, BLUE=4
type Omega = Unsigned 3

-- | Radius: Intensity scalar (0-255, 8 bits)
-- Maps to 0.0-1.0 in software
type Radius = Unsigned 8

-- | Reserved/CRC field (13 bits)
type Reserved = Unsigned 13

-- | Full 32-bit RPP Canonical Address
type RPPAddress = Unsigned 32

-- | Coherence level (0-255, mapped to 0.0-1.0)
type Coherence = Unsigned 8

-- =============================================================================
-- SEMANTIC TYPES (Ra System)
-- =============================================================================

-- | ThetaSector: 8 semantic sectors derived from 27 Repitans
data ThetaSector
  = SectorCore      -- Repitans 1-3: Core identity, Ra-foundation
  | SectorGene      -- Repitans 4-6: Genetic/ancestral encoding
  | SectorMemory    -- Repitans 7-10: Memory lattice, experience storage
  | SectorWitness   -- Repitans 11-13: Witness field, observation points
  | SectorDream     -- Repitans 14-17: Dream surface, subconscious
  | SectorBridge    -- Repitans 18-20: Bridge nodes, translation layer
  | SectorGuardian  -- Repitans 21-24: Guardian zones, protection
  | SectorShadow    -- Repitans 25-27: Shadow integration, hidden aspects
  deriving (Show, Eq, Generic, NFDataX, ShowX)

-- | RACBand: 6 access sensitivity levels
data RACBand
  = RAC1  -- Highest sensitivity (sacred/protected)
  | RAC2  -- High sensitivity
  | RAC3  -- Moderate sensitivity
  | RAC4  -- Standard access
  | RAC5  -- Low sensitivity
  | RAC6  -- Public/unrestricted
  deriving (Show, Eq, Generic, NFDataX)

-- | OmegaTier: 5 coherence/quality tiers
data OmegaTier
  = TierRed        -- Tier 0: Alert/critical
  | TierOmegaMajor -- Tier 1: Major transition
  | TierGreen      -- Tier 2: Stable/optimal
  | TierOmegaMinor -- Tier 3: Minor transition
  | TierBlue       -- Tier 4: Calm/integration
  deriving (Show, Eq, Generic, NFDataX)

-- | Consent state (matches ACSP - Avatar Consent State Protocol)
data ConsentState
  = FullConsent       -- Full access granted
  | AttentiveConsent  -- Heightened monitoring
  | DiminishedConsent -- Reduced capacity
  | SuspendedConsent  -- Temporarily suspended
  | EmergencyOverride -- Override for safety
  deriving (Show, Eq, Generic, NFDataX)

-- =============================================================================
-- ADDRESS ENCODING/DECODING
-- =============================================================================

-- | Encode components into 32-bit RPP canonical address
encodeAddress :: Theta -> Phi -> Omega -> Radius -> Reserved -> RPPAddress
encodeAddress theta phi omega radius reserved =
  (extend theta `shiftL` 27) .|.
  (extend phi `shiftL` 24) .|.
  (extend omega `shiftL` 21) .|.
  (extend radius `shiftL` 13) .|.
  extend reserved

-- | Decode 32-bit address into components
decodeAddress :: RPPAddress -> (Theta, Phi, Omega, Radius, Reserved)
decodeAddress addr = (theta, phi, omega, radius, reserved)
  where
    theta    = resize (addr `shiftR` 27)
    phi      = resize (addr `shiftR` 24) .&. 0x7
    omega    = resize (addr `shiftR` 21) .&. 0x7
    radius   = resize (addr `shiftR` 13) .&. 0xFF
    reserved = resize addr .&. 0x1FFF

-- | Map theta (1-27) to ThetaSector
thetaToSector :: Theta -> ThetaSector
thetaToSector theta
  | theta <= 3  = SectorCore
  | theta <= 6  = SectorGene
  | theta <= 10 = SectorMemory
  | theta <= 13 = SectorWitness
  | theta <= 17 = SectorDream
  | theta <= 20 = SectorBridge
  | theta <= 24 = SectorGuardian
  | otherwise   = SectorShadow

-- | Map phi (1-6) to RACBand
phiToRAC :: Phi -> RACBand
phiToRAC 1 = RAC1
phiToRAC 2 = RAC2
phiToRAC 3 = RAC3
phiToRAC 4 = RAC4
phiToRAC 5 = RAC5
phiToRAC _ = RAC6

-- | Map omega (0-4) to OmegaTier
omegaToTier :: Omega -> OmegaTier
omegaToTier 0 = TierRed
omegaToTier 1 = TierOmegaMajor
omegaToTier 2 = TierGreen
omegaToTier 3 = TierOmegaMinor
omegaToTier _ = TierBlue

-- | Encode ThetaSector to 3-bit value
encodeSector :: ThetaSector -> Unsigned 3
encodeSector SectorCore     = 0
encodeSector SectorGene     = 1
encodeSector SectorMemory   = 2
encodeSector SectorWitness  = 3
encodeSector SectorDream    = 4
encodeSector SectorBridge   = 5
encodeSector SectorGuardian = 6
encodeSector SectorShadow   = 7

-- =============================================================================
-- VALIDITY CHECKS
-- =============================================================================

-- | Check if theta is in valid Repitan range (1-27)
validTheta :: Theta -> Bool
validTheta theta = theta >= 1 && theta <= 27

-- | Check if phi is in valid RAC range (1-6)
validPhi :: Phi -> Bool
validPhi phi = phi >= 1 && phi <= 6

-- | Check if omega is in valid tier range (0-4)
validOmega :: Omega -> Bool
validOmega omega = omega <= 4

-- | Full address validation
validAddress :: RPPAddress -> Bool
validAddress addr = validTheta theta && validPhi phi && validOmega omega
  where
    (theta, phi, omega, _, _) = decodeAddress addr

-- | Check for null address (theta = 0)
isNullAddress :: RPPAddress -> Bool
isNullAddress addr = theta == 0
  where
    (theta, _, _, _, _) = decodeAddress addr

-- | Check for wildcard (reserved values)
isWildcard :: RPPAddress -> Bool
isWildcard addr = theta == 31 || phi == 7 || omega == 7
  where
    (theta, phi, omega, _, _) = decodeAddress addr

-- =============================================================================
-- SECTOR ADJACENCY (Ra topology)
-- =============================================================================

-- | Check if two sectors are adjacent in Ra topology
sectorsAdjacent :: ThetaSector -> ThetaSector -> Bool
sectorsAdjacent SectorCore SectorGene      = True
sectorsAdjacent SectorCore SectorMemory    = True
sectorsAdjacent SectorGene SectorCore      = True
sectorsAdjacent SectorGene SectorBridge    = True
sectorsAdjacent SectorGene SectorGuardian  = True
sectorsAdjacent SectorMemory SectorCore    = True
sectorsAdjacent SectorMemory SectorWitness = True
sectorsAdjacent SectorMemory SectorBridge  = True
sectorsAdjacent SectorWitness SectorMemory = True
sectorsAdjacent SectorWitness SectorBridge = True
sectorsAdjacent SectorDream SectorBridge   = True
sectorsAdjacent SectorDream SectorShadow   = True
sectorsAdjacent SectorBridge SectorGene    = True
sectorsAdjacent SectorBridge SectorMemory  = True
sectorsAdjacent SectorBridge SectorWitness = True
sectorsAdjacent SectorBridge SectorDream   = True
sectorsAdjacent SectorBridge SectorGuardian = True
sectorsAdjacent SectorGuardian SectorGene  = True
sectorsAdjacent SectorGuardian SectorBridge = True
sectorsAdjacent SectorShadow SectorDream   = True
sectorsAdjacent _ _ = False

-- =============================================================================
-- COHERENCE CALCULATION
-- =============================================================================

-- | Weight constants for coherence calculation (fixed-point: value * 256)
wTheta, wPhi, wOmega, wRadius :: Unsigned 8
wTheta  = 77   -- 0.30 * 256
wPhi    = 102  -- 0.40 * 256
wOmega  = 51   -- 0.20 * 256
wRadius = 26   -- 0.10 * 256

-- | Calculate coherence between two addresses
calculateCoherence :: RPPAddress -> RPPAddress -> Coherence
calculateCoherence addr1 addr2 =
  if dist > 255 then 0 else 255 - resize dist
  where
    (t1, p1, o1, r1, _) = decodeAddress addr1
    (t2, p2, o2, r2, _) = decodeAddress addr2

    -- Theta distance (circular on 27 Repitans)
    thetaDiff = if t1 > t2 then t1 - t2 else t2 - t1
    thetaDist = if thetaDiff > 13 then 27 - resize thetaDiff else resize thetaDiff

    -- Phi distance (linear 1-6)
    phiDist = if p1 > p2 then p1 - p2 else p2 - p1

    -- Omega distance (linear 0-4)
    omegaDist = if o1 > o2 then o1 - o2 else o2 - o1

    -- Radius distance (linear 0-255)
    radiusDist = if r1 > r2 then r1 - r2 else r2 - r1

    -- Weighted distance
    dist :: Unsigned 16
    dist = (extend thetaDist * 20 * extend wTheta) `shiftR` 8 +
           (extend phiDist * 51 * extend wPhi) `shiftR` 8 +
           (extend omegaDist * 64 * extend wOmega) `shiftR` 8 +
           (extend radiusDist * extend wRadius) `shiftR` 8

-- =============================================================================
-- CONSENT GATING
-- =============================================================================

-- | Coherence thresholds for consent states
coherenceStable, coherenceMarginal, coherenceCritical :: Coherence
coherenceStable   = 179  -- 0.70 * 255
coherenceMarginal = 128  -- 0.50 * 255
coherenceCritical = 51   -- 0.20 * 255

-- | Map coherence to consent state
coherenceToConsent :: Coherence -> ConsentState
coherenceToConsent coh
  | coh >= coherenceStable   = FullConsent
  | coh >= coherenceMarginal = AttentiveConsent
  | coh >= coherenceCritical = DiminishedConsent
  | coh > 0                  = SuspendedConsent
  | otherwise                = EmergencyOverride

-- | Check if access is permitted
accessPermitted :: ConsentState -> Bool
accessPermitted FullConsent      = True
accessPermitted AttentiveConsent = True
accessPermitted _                = False

-- =============================================================================
-- SECTOR COHERENCE REQUIREMENTS
-- =============================================================================

-- | Minimum coherence required for sector access
sectorMinCoherence :: ThetaSector -> Coherence
sectorMinCoherence SectorCore     = 204  -- 0.80 (highest protection)
sectorMinCoherence SectorGene     = 153  -- 0.60
sectorMinCoherence SectorMemory   = 191  -- 0.75
sectorMinCoherence SectorWitness  = 102  -- 0.40
sectorMinCoherence SectorDream    = 128  -- 0.50
sectorMinCoherence SectorBridge   = 179  -- 0.70
sectorMinCoherence SectorGuardian = 191  -- 0.75
sectorMinCoherence SectorShadow   = 77   -- 0.30 (most accessible)

-- =============================================================================
-- CONTROLLER STATE MACHINE
-- =============================================================================

-- | Controller state
data ControllerState = ControllerState
  { csCurrentAddress :: RPPAddress
  , csCoherence      :: Coherence
  , csConsentState   :: ConsentState
  , csCycleCount     :: Unsigned 32
  } deriving (Show, Eq, Generic, NFDataX)

-- | Controller input
data ControllerInput = ControllerInput
  { ciTargetAddress :: RPPAddress
  , ciCompareAddr   :: RPPAddress
  , ciReset         :: Bool
  } deriving (Show, Eq, Generic, NFDataX)

-- | Controller output
data ControllerOutput = ControllerOutput
  { coCurrentSector :: ThetaSector
  , coRACBand       :: RACBand
  , coOmegaTier     :: OmegaTier
  , coCoherence     :: Coherence
  , coConsentState  :: ConsentState
  , coAccessGranted :: Bool
  , coAddressValid  :: Bool
  } deriving (Show, Eq, Generic, NFDataX)

-- | Initial state
initialState :: ControllerState
initialState = ControllerState
  { csCurrentAddress = encodeAddress 10 3 2 128 0  -- MEMORY sector, RAC3, GREEN tier
  , csCoherence      = coherenceStable
  , csConsentState   = FullConsent
  , csCycleCount     = 0
  }

-- | Controller transition function
controllerT :: ControllerState -> ControllerInput -> (ControllerState, ControllerOutput)
controllerT state@ControllerState{..} ControllerInput{..}
  | ciReset = (initialState, defaultOutput)
  | otherwise = (state', output)
  where
    -- Decode target address
    (theta, phi, omega, radius, _) = decodeAddress ciTargetAddress

    -- Get semantic components
    sector = thetaToSector theta
    rac = phiToRAC phi
    tier = omegaToTier omega

    -- Calculate coherence with comparison address
    coherence' = calculateCoherence ciTargetAddress ciCompareAddr

    -- Determine consent state
    consent' = coherenceToConsent coherence'

    -- Check validity
    addrValid = validAddress ciTargetAddress

    -- Check access (must meet sector minimum coherence)
    sectorOk = coherence' >= sectorMinCoherence sector
    accessOk = accessPermitted consent' && sectorOk && addrValid

    -- Update state
    state' = state
      { csCurrentAddress = ciTargetAddress
      , csCoherence      = coherence'
      , csConsentState   = consent'
      , csCycleCount     = csCycleCount + 1
      }

    -- Generate output
    output = ControllerOutput
      { coCurrentSector = sector
      , coRACBand       = rac
      , coOmegaTier     = tier
      , coCoherence     = coherence'
      , coConsentState  = consent'
      , coAccessGranted = accessOk
      , coAddressValid  = addrValid
      }

    defaultOutput = ControllerOutput SectorCore RAC6 TierGreen 0 EmergencyOverride False False

-- | Mealy machine wrapper
rppController
  :: HiddenClockResetEnable dom
  => Signal dom ControllerInput
  -> Signal dom ControllerOutput
rppController = mealy controllerT initialState

-- =============================================================================
-- TOP-LEVEL ENTITY
-- =============================================================================

{-# ANN topEntity
  (Synthesize
    { t_name = "rpp_canonical_controller"
    , t_inputs =
        [ PortName "clk"
        , PortName "rst"
        , PortName "en"
        , PortName "target_address"
        , PortName "compare_address"
        ]
    , t_output = PortProduct ""
        [ PortName "sector"
        , PortName "rac_band"
        , PortName "omega_tier"
        , PortName "coherence"
        , PortName "consent_state"
        , PortName "access_granted"
        , PortName "address_valid"
        ]
    }) #-}

topEntity
  :: Clock System
  -> Reset System
  -> Enable System
  -> Signal System RPPAddress      -- target_address
  -> Signal System RPPAddress      -- compare_address
  -> Signal System
      ( Unsigned 3                 -- sector (encoded)
      , Unsigned 3                 -- rac_band (encoded)
      , Unsigned 3                 -- omega_tier (encoded)
      , Coherence                  -- coherence
      , Unsigned 3                 -- consent_state (encoded)
      , Bool                       -- access_granted
      , Bool                       -- address_valid
      )
topEntity clk rst en target compare =
  withClockResetEnable clk rst en $
    fmap formatOutput (rppController input)
  where
    input = mkInput <$> target <*> compare

    mkInput t c = ControllerInput
      { ciTargetAddress = t
      , ciCompareAddr   = c
      , ciReset         = False
      }

    formatOutput ControllerOutput{..} =
      ( encodeSector coCurrentSector
      , encodeRAC coRACBand
      , encodeTier coOmegaTier
      , coCoherence
      , encodeConsent coConsentState
      , coAccessGranted
      , coAddressValid
      )

    encodeRAC RAC1 = 1
    encodeRAC RAC2 = 2
    encodeRAC RAC3 = 3
    encodeRAC RAC4 = 4
    encodeRAC RAC5 = 5
    encodeRAC RAC6 = 6

    encodeTier TierRed        = 0
    encodeTier TierOmegaMajor = 1
    encodeTier TierGreen      = 2
    encodeTier TierOmegaMinor = 3
    encodeTier TierBlue       = 4

    encodeConsent FullConsent       = 0
    encodeConsent AttentiveConsent  = 1
    encodeConsent DiminishedConsent = 2
    encodeConsent SuspendedConsent  = 3
    encodeConsent EmergencyOverride = 4

-- =============================================================================
-- TESTBENCH
-- =============================================================================

testBench :: Signal System Bool
testBench = done
  where
    -- Test addresses: MEMORY sector, RAC3, GREEN tier, radius 128
    testAddr1 = encodeAddress 10 3 2 128 0  -- MEMORY
    testAddr2 = encodeAddress 10 3 2 130 0  -- Similar (high coherence)
    testAddr3 = encodeAddress 25 1 0 50 0   -- SHADOW, RAC1, RED (low coherence)

    testStimuli :: Vec 4 ControllerInput
    testStimuli = ControllerInput testAddr1 testAddr1 False
               :> ControllerInput testAddr1 testAddr2 False
               :> ControllerInput testAddr3 testAddr1 False
               :> ControllerInput testAddr1 testAddr1 True  -- Reset
               :> Nil

    testInput = stimuliGenerator clk rst testStimuli

    clk = tbSystemClockGen (not <$> done)
    rst = systemResetGen
    en = enableGen

    output = withClockResetEnable clk rst en $
      fmap coCurrentSector (rppController testInput)

    expectedSectors :: Vec 4 ThetaSector
    expectedSectors = SectorMemory :> SectorMemory :> SectorShadow :> SectorCore :> Nil

    expectOutput = outputVerifier' clk rst expectedSectors
    done = expectOutput output
