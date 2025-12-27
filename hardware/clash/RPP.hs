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
Module      : RPP
Description : Rotational Packet Protocol FPGA Implementation
Copyright   : (c) Alexander Liam Lennon, 2024
License     : Apache-2.0

Clash implementation of the Rotational Packet Protocol (RPP) for
angular memory access and TRB zone detection.

This module is part of the RPP open specification.
Repository: https://github.com/anywave/rpp-spec

Key Features:
- Phase-encoded memory addressing (9-bit theta, 8-bit phi)
- TRB zone detection with configurable thresholds
- Fibonacci skip pattern generator
- Coherence monitoring and consent gating
- Holographic file emergence detection

Hardware Targets:
- Xilinx 7-series (Artix-7, Kintex-7)
- Intel Cyclone V / Arria 10
- Lattice ECP5

Usage:
  # Generate Verilog
  clash --verilog RPP.hs

  # Generate VHDL
  clash --vhdl RPP.hs

  # Simulate
  clash -i. --interactive RPP.hs
-}

module RPP where

import Clash.Prelude
import Clash.Explicit.Testbench
import GHC.Generics (Generic)

-- =============================================================================
-- TYPE DEFINITIONS
-- =============================================================================

-- | Angular position with 1-degree resolution
-- Theta: 0-359 (9 bits), Phi: -90 to +90 mapped to 0-180 (8 bits)
type Theta = Unsigned 9  -- 0-511, but we use 0-359
type Phi = Unsigned 8    -- 0-255, we use 0-180

-- | Coherence level (0-255, mapped to 0.0-1.0)
type Coherence = Unsigned 8

-- | Phase value for timing (0-359 degrees)
type Phase = Unsigned 9

-- | Memory address (13 bits for 360x181 = 65160 locations)
type MemAddr = Unsigned 17

-- | TRB zone identifier
data TRBZone
  = NoZone
  | GeneMap        -- TRB_01: theta 0-90, phi 45-135 (equatorial)
  | MemoryLattice  -- TRB_02: theta 90-180
  | WitnessField   -- TRB_03: theta 180-270
  | Integration    -- TRB_04: theta 270-360, phi 135-180 (north)
  | Grounding      -- TRB_05: full theta, phi 0-45 (south)
  deriving (Show, Eq, Generic, NFDataX, ShowX)

-- | Consent state for access gating
data ConsentState
  = FullConsent
  | DiminishedConsent
  | SuspendedConsent
  | EmergencyOverride
  deriving (Show, Eq, Generic, NFDataX)

-- | Skip pattern type
data SkipPattern
  = NoSkip
  | Fibonacci
  | Prime
  | Harmonic
  deriving (Show, Eq, Generic, NFDataX)

-- | Packet state for intersection detection
data PacketState = PacketState
  { psTheta      :: Theta
  , psPhi        :: Phi
  , psCoherence  :: Coherence
  , psPhase      :: Phase
  , psActive     :: Bool
  , psSkipType   :: SkipPattern
  } deriving (Show, Eq, Generic, NFDataX)

-- | TRB activation result
data TRBActivation = TRBActivation
  { taZone       :: TRBZone
  , taCoherence  :: Coherence
  , taAmplitude  :: Unsigned 8
  , taTimestamp  :: Unsigned 32
  , taValid      :: Bool
  } deriving (Show, Eq, Generic, NFDataX)

-- | Angular access controller state
data ControllerState = ControllerState
  { csCurrentTheta    :: Theta
  , csCurrentPhi      :: Phi
  , csCurrentPhase    :: Phase
  , csCoherence       :: Coherence
  , csConsentState    :: ConsentState
  , csActivePackets   :: Vec 8 PacketState
  , csPacketCount     :: Unsigned 4
  , csTRBActivations  :: Vec 4 TRBActivation
  , csActivationCount :: Unsigned 3
  , csCycleCount      :: Unsigned 32
  , csSkipIndex       :: Unsigned 4
  } deriving (Show, Eq, Generic, NFDataX)

-- =============================================================================
-- CONSTANTS
-- =============================================================================

-- | Golden angle in fixed-point (137.5077... degrees * 256)
goldenAngleFixed :: Unsigned 16
goldenAngleFixed = 35202  -- 137.5077 * 256

-- | Coherence thresholds
coherenceStable :: Coherence
coherenceStable = 179  -- 0.7 * 255

coherenceMarginal :: Coherence
coherenceMarginal = 102  -- 0.4 * 255

coherenceCritical :: Coherence
coherenceCritical = 51  -- 0.2 * 255

-- | Phase tolerance for alignment (degrees)
phaseTolerance :: Phase
phaseTolerance = 15

-- =============================================================================
-- TRB ZONE DETECTION
-- =============================================================================

-- | Check if point is in TRB zone
-- Maps angular coordinates to TRB zones based on RPP sector definitions
detectTRBZone :: Theta -> Phi -> TRBZone
detectTRBZone theta phi
  -- Grounding zone: full theta, phi 0-45 (south pole)
  | phi < 45 = Grounding

  -- Gene Map: theta 0-90, equatorial band
  | theta < 90 && phi >= 45 && phi <= 135 = GeneMap

  -- Memory Lattice: theta 90-180, equatorial band
  | theta >= 90 && theta < 180 && phi >= 45 && phi <= 135 = MemoryLattice

  -- Witness Field: theta 180-270, equatorial band
  | theta >= 180 && theta < 270 && phi >= 45 && phi <= 135 = WitnessField

  -- Integration: theta 270-360, north pole (phi 135-180)
  | theta >= 270 && phi > 135 = Integration

  -- No zone match
  | otherwise = NoZone

-- | TRB zone coherence requirements
zoneMinCoherence :: TRBZone -> Coherence
zoneMinCoherence GeneMap       = 153  -- 0.6
zoneMinCoherence MemoryLattice = 191  -- 0.75
zoneMinCoherence WitnessField  = 102  -- 0.4
zoneMinCoherence Integration   = 179  -- 0.7
zoneMinCoherence Grounding     = 77   -- 0.3
zoneMinCoherence NoZone        = 255  -- Never activate

-- | Check if TRB activation conditions are met
checkTRBActivation
  :: TRBZone
  -> Coherence
  -> Unsigned 4  -- Packet count
  -> Bool        -- Phase aligned
  -> Bool
checkTRBActivation NoZone _ _ _ = False
checkTRBActivation zone coh count aligned =
  coh >= zoneMinCoherence zone &&
  count >= minPackets &&
  (not requiresPhase || aligned)
  where
    minPackets = case zone of
      Integration -> 3
      _           -> 2
    requiresPhase = case zone of
      WitnessField -> False
      Grounding    -> False
      _            -> True

-- =============================================================================
-- SKIP PATTERN GENERATION
-- =============================================================================

-- | Generate Fibonacci skip angle
fibonacciSkip :: Unsigned 4 -> Theta
fibonacciSkip idx = resize ((extend idx * goldenAngleFixed) `shiftR` 8) `mod` 360

-- | Prime numbers for prime skip pattern
primeTable :: Vec 8 (Unsigned 5)
primeTable = 2 :> 3 :> 5 :> 7 :> 11 :> 13 :> 17 :> 19 :> Nil

-- | Generate prime skip angle
primeSkip :: Unsigned 4 -> Theta
primeSkip idx = resize (prime * 8) `mod` 360
  where
    -- Use modulo to ensure valid index
    safeIdx = resize idx `mod` 8 :: Unsigned 3
    prime = primeTable !! safeIdx

-- | Get skip angle based on pattern type
getSkipAngle :: SkipPattern -> Unsigned 4 -> Theta
getSkipAngle NoSkip    _ = 0
getSkipAngle Fibonacci i = fibonacciSkip i
getSkipAngle Prime     i = primeSkip i
getSkipAngle Harmonic  i = resize (i * 45) `mod` 360  -- 45-degree steps

-- =============================================================================
-- PHASE ALIGNMENT CHECK
-- =============================================================================

-- | Check if two phases are aligned within tolerance
phaseAligned :: Phase -> Phase -> Bool
phaseAligned p1 p2 = diff <= phaseTolerance || diff >= (360 - phaseTolerance)
  where
    diff = if p1 > p2 then p1 - p2 else p2 - p1

-- | Check if all active packets are phase-aligned
-- In hardware, we check pairs of adjacent active packets
allPhasesAligned :: Vec 8 PacketState -> Unsigned 4 -> Bool
allPhasesAligned packets count
  | count < 2 = True
  | otherwise = fold (&&) (zipWith checkPair packets rotatedPackets)
  where
    rotatedPackets = rotateLeftS packets d1
    checkPair p1 p2
      | psActive p1 && psActive p2 = phaseAligned (psPhase p1) (psPhase p2)
      | otherwise = True

-- =============================================================================
-- CONSENT GATING
-- =============================================================================

-- | Map coherence to consent state
coherenceToConsent :: Coherence -> ConsentState
coherenceToConsent coh
  | coh >= coherenceStable   = FullConsent
  | coh >= coherenceMarginal = DiminishedConsent
  | coh >= coherenceCritical = SuspendedConsent
  | otherwise                = EmergencyOverride

-- | Check if access is permitted for consent state
accessPermitted :: ConsentState -> Bool
accessPermitted FullConsent       = True
accessPermitted DiminishedConsent = True  -- With delay
accessPermitted SuspendedConsent  = False
accessPermitted EmergencyOverride = False

-- =============================================================================
-- MEMORY ADDRESS GENERATION
-- =============================================================================

-- | Convert angular coordinates to linear memory address
-- Address = theta * 181 + phi (for 360x181 memory)
angularToAddress :: Theta -> Phi -> MemAddr
angularToAddress theta phi = extend theta * 181 + extend phi

-- | Convert address back to angular coordinates
addressToAngular :: MemAddr -> (Theta, Phi)
addressToAngular addr = (resize theta, resize phi)
  where
    theta = addr `div` 181
    phi = addr `mod` 181

-- =============================================================================
-- MAIN CONTROLLER STATE MACHINE
-- =============================================================================

-- | Controller input signals
data ControllerInput = ControllerInput
  { ciNewPacket    :: Maybe PacketState
  , ciRemovePacket :: Maybe (Unsigned 4)
  , ciQueryTheta   :: Theta
  , ciQueryPhi     :: Phi
  , ciReset        :: Bool
  } deriving (Show, Eq, Generic, NFDataX)

-- | Controller output signals
data ControllerOutput = ControllerOutput
  { coMemAddress     :: MemAddr
  , coMemRead        :: Bool
  , coMemWrite       :: Bool
  , coTRBActivation  :: Maybe TRBActivation
  , coConsentState   :: ConsentState
  , coAccessGranted  :: Bool
  , coCurrentZone    :: TRBZone
  , coSkipAngle      :: Theta
  } deriving (Show, Eq, Generic, NFDataX)

-- | Initial controller state
initialState :: ControllerState
initialState = ControllerState
  { csCurrentTheta    = 0
  , csCurrentPhi      = 90  -- Equator
  , csCurrentPhase    = 0
  , csCoherence       = coherenceStable
  , csConsentState    = FullConsent
  , csActivePackets   = repeat emptyPacket
  , csPacketCount     = 0
  , csTRBActivations  = repeat emptyActivation
  , csActivationCount = 0
  , csCycleCount      = 0
  , csSkipIndex       = 0
  }
  where
    emptyPacket = PacketState 0 0 0 0 False NoSkip
    emptyActivation = TRBActivation NoZone 0 0 0 False

-- | Main controller transition function
controllerT
  :: ControllerState
  -> ControllerInput
  -> (ControllerState, ControllerOutput)
controllerT state@ControllerState{..} input@ControllerInput{..}
  | ciReset = (initialState, defaultOutput)
  | otherwise = (state', output)
  where
    -- Update cycle counter
    cycleCount' = csCycleCount + 1

    -- Update phase (1 degree per cycle for now)
    phase' = (csCurrentPhase + 1) `mod` 360

    -- Update position to query position
    theta' = ciQueryTheta
    phi' = ciQueryPhi

    -- Detect current TRB zone
    currentZone = detectTRBZone theta' phi'

    -- Check phase alignment
    phasesAligned = allPhasesAligned csActivePackets csPacketCount

    -- Check TRB activation
    trbActivated = checkTRBActivation currentZone csCoherence csPacketCount phasesAligned

    -- Create activation record if triggered
    newActivation = if trbActivated && not (any taValid csTRBActivations)
      then Just $ TRBActivation currentZone csCoherence 128 cycleCount' True
      else Nothing

    -- Update consent state
    consent' = coherenceToConsent csCoherence

    -- Check access permission
    accessGranted = accessPermitted consent'

    -- Generate skip angle
    skipAngle = getSkipAngle Fibonacci csSkipIndex
    skipIndex' = (csSkipIndex + 1) `mod` 8

    -- Calculate memory address
    memAddr = angularToAddress theta' phi'

    -- Update state
    state' = state
      { csCurrentTheta   = theta'
      , csCurrentPhi     = phi'
      , csCurrentPhase   = phase'
      , csConsentState   = consent'
      , csCycleCount     = cycleCount'
      , csSkipIndex      = skipIndex'
      }

    -- Generate output
    output = ControllerOutput
      { coMemAddress    = memAddr
      , coMemRead       = accessGranted
      , coMemWrite      = False
      , coTRBActivation = newActivation
      , coConsentState  = consent'
      , coAccessGranted = accessGranted
      , coCurrentZone   = currentZone
      , coSkipAngle     = skipAngle
      }

    defaultOutput = ControllerOutput 0 False False Nothing FullConsent False NoZone 0

-- | Mealy machine wrapper for synthesis
angularController
  :: HiddenClockResetEnable dom
  => Signal dom ControllerInput
  -> Signal dom ControllerOutput
angularController = mealy controllerT initialState

-- =============================================================================
-- TOP-LEVEL ENTITY
-- =============================================================================

{-# ANN topEntity
  (Synthesize
    { t_name = "rpp_controller"
    , t_inputs =
        [ PortName "clk"
        , PortName "rst"
        , PortName "en"
        , PortName "query_theta"
        , PortName "query_phi"
        , PortName "coherence"
        , PortName "packet_valid"
        , PortName "packet_theta"
        , PortName "packet_phi"
        ]
    , t_output = PortProduct ""
        [ PortName "mem_addr"
        , PortName "mem_read"
        , PortName "access_granted"
        , PortName "trb_zone"
        , PortName "consent_state"
        , PortName "skip_angle"
        ]
    }) #-}

topEntity
  :: Clock System
  -> Reset System
  -> Enable System
  -> Signal System Theta          -- query_theta
  -> Signal System Phi            -- query_phi
  -> Signal System Coherence      -- coherence
  -> Signal System Bool           -- packet_valid
  -> Signal System Theta          -- packet_theta
  -> Signal System Phi            -- packet_phi
  -> Signal System
      ( MemAddr                   -- mem_addr
      , Bool                      -- mem_read
      , Bool                      -- access_granted
      , Unsigned 3                -- trb_zone (encoded)
      , Unsigned 2                -- consent_state (encoded)
      , Theta                     -- skip_angle
      )
topEntity clk rst en qTheta qPhi coh pValid pTheta pPhi =
  withClockResetEnable clk rst en $
    fmap formatOutput (angularController input)
  where
    input = mkInput <$> qTheta <*> qPhi <*> coh <*> pValid <*> pTheta <*> pPhi

    mkInput qt qp c pv pt pp = ControllerInput
      { ciNewPacket = if pv
          then Just $ PacketState pt pp c 0 True Fibonacci
          else Nothing
      , ciRemovePacket = Nothing
      , ciQueryTheta = qt
      , ciQueryPhi = qp
      , ciReset = False
      }

    formatOutput ControllerOutput{..} =
      ( coMemAddress
      , coMemRead
      , coAccessGranted
      , encodeZone coCurrentZone
      , encodeConsent coConsentState
      , coSkipAngle
      )

    encodeZone NoZone        = 0
    encodeZone GeneMap       = 1
    encodeZone MemoryLattice = 2
    encodeZone WitnessField  = 3
    encodeZone Integration   = 4
    encodeZone Grounding     = 5

    encodeConsent FullConsent       = 0
    encodeConsent DiminishedConsent = 1
    encodeConsent SuspendedConsent  = 2
    encodeConsent EmergencyOverride = 3

-- =============================================================================
-- TESTBENCH
-- =============================================================================

-- | Simple testbench for simulation
testBench :: Signal System Bool
testBench = done
  where
    testInput = stimuliGenerator clk rst testStimuli

    testStimuli :: Vec 5 ControllerInput
    testStimuli = ControllerInput Nothing Nothing 45 90 False
              :> ControllerInput Nothing Nothing 90 90 False
              :> ControllerInput Nothing Nothing 135 90 False
              :> ControllerInput Nothing Nothing 225 90 False
              :> ControllerInput Nothing Nothing 315 150 False
              :> Nil

    expectOutput = outputVerifier' clk rst expectedZones

    expectedZones :: Vec 5 TRBZone
    expectedZones = GeneMap
                :> MemoryLattice
                :> MemoryLattice
                :> WitnessField
                :> Integration
                :> Nil

    clk = tbSystemClockGen (not <$> done)
    rst = systemResetGen
    en = enableGen

    output = withClockResetEnable clk rst en $
      fmap coCurrentZone (angularController testInput)

    done = expectOutput output
