# mnc.py
# Movements, Not Chords by Trevor Ritchie
#
# This program is a musical instrument, 
# played with touch and accelerometer inputs from the TouchOSC mobile app on a smartphone.
# See the README for detailed performance instructions and a brief introduction to the music theory.

from midi import *
from music import *
from osc import *
from timer import *
import sys

######## USER SETTINGS #########
TRANSPOSE_KEY_SEMITONES = -3  # 0 = C, 2 = D, -2 = Bb, +10 = Bb, etc.
BASS = True                   # want a bass root note for each chord numeral?
DECAY = False                 # want notes to decay quicker?
DECAY_TIME_MS = 10            # time between each volume decrement in ms
OSC_LISTENER_PORT = 50380     # what port do you want to send OSC messages to?

# Choose MIDI Sounds
# For all instrument constants, see https://jythonmusic.me/api/midi-constants/instrument/
Play.setInstrument(NYLON_GUITAR, 0)  # channel 0 for top 4 voices
Play.setInstrument(SAWTOOTH, 1)      # channel 1 for bass
################################

# region MIDI Sound Suggestions:
# Play.setInstrument(PIANO, 0) 
# Play.setInstrument(JAZZ_GUITAR, 0) 
# Play.setInstrument(DISTORTION_GUITAR, 0)
# Play.setInstrument(SQUARE, 0) 
# Play.setInstrument(SAWTOOTH, 0) 
# Play.setInstrument(SQUARE, 1) 
# Play.setInstrument(ACOUSTIC_BASS, 1) 
# Play.setInstrument(DISTORTION_GUITAR, 1)
# endregion

# region Constants
# Scales of chords by "pitch class". Semitones are assigned to 0-11. 
MAJOR_SIXTH_DIMINISHED_SCALE = [0, 2, 4, 5, 7, 8, 9, 11]    
MAJOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD = [0, 1, 3, 4, 5, 7, 8, 10]   
MAJOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH = [0, 1, 2, 4, 5, 7, 9, 10]   
MINOR_SEVENTH_DIMINISHED_SCALE = [0, 2, 3, 5, 7, 8, 10, 11] # aka major sixth diminished scale from sixth

MINOR_SIXTH_DIMINISHED_SCALE = [0, 2, 3, 5, 7, 8, 9, 11] 
MINOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD = [0, 2, 4, 5, 6, 8, 9, 11] 
MINOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH = [0, 1, 2, 4, 5, 7, 8, 10]
MINOR_SEVENTH_FLAT_FIVE_DIMINISHED_SCALE = [0, 2, 3, 5, 6, 8, 10, 11] # aka minor sixth diminished scale from sixth

DOMINANT_SEVENTH_DIMINISHED_SCALE = [0, 2, 4, 5, 7, 8, 10, 11]
DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_THIRD = [0, 1, 3, 4, 6, 7, 8, 10] 
DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_FIFTH = [0, 1, 3, 4, 5, 7, 9, 10, ]
DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_SEVENTH = [0, 1, 2, 4, 6, 7, 9, 10]

DOMINANT_SEVENTH_FLAT_FIVE_DIMINISHED_SCALE = [0, 2, 4, 5, 6, 8, 10, 11]
DOMINANT_ROOTS_AND_THEIR_DIMINISHED = [0, 2, 3, 5, 6, 8, 9, 11] # aka whole-half diminished scale

# Mapping chord numerals of a key to button names
chordNumeralToButtonNameDict = {
    1 : "16",
    2: "12",
    3 : "h8",
    4 : "h4",
    5 : "15",
    6: "11",
    7 : "h7",
    8 : "h3"
}

KEY = MAJOR_SCALE  # 7 note scales, different from the "scales of chords". Used to follow typical chord progression notations.
OCTAVE = 12  # 12 semitones in an octave
BASS_OCTAVE_OFFSET =  OCTAVE * 3
# endregion

# region Global Variables
scaleOfChords = MAJOR_SIXTH_DIMINISHED_SCALE # choose a chord scale to move through
scaleOfChordsRoot = KEY[0] # the root of the scale of chords
pivotPitch = OCTAVE * 5 # the note around which the contrary motion expands/shrinks
                # if the pivot pitch is played, only that single pitch will sound
bassNote = OCTAVE * 4
keysPressed = 0
buttonsHeld = 0
lastChord = []
chordNumeral = 1
offChordLock = False
alternate = False # alternate scale of chords for each chord numeral in the key
dominant = False
familyUp = False
familyDown = False
familyAcross = False
accelerometerValues = []
# endregion

# region Functions
# turn volume down on a repeating timer to achieve decay effect
def decay(channel):
    currentVolume = Play.getVolume(channel)
    newVolume = max(currentVolume - 3, 0)  # Ensure volume doesn't go below 0

    Play.setVolume(newVolume)
    if newVolume == 0: 
        Play.allNotesOff()

# timer to call decay()
decayTimer = Timer(DECAY_TIME_MS, decay, [0], True)

# Parse accelerometer data from OSC messages
def parseAccelerometerData(message):
    global accelerometerValues

    address = message.getAddress()
    accelerometerValues = message.getArguments()

# Map accelerometer values to pitches
def mapAccelerometerToPitch(x, y, z):
    global scaleOfChords, scaleOfChordsRoot, offChordLock

    # Ensure x and y are within range
    if x > 0.0: x = 0.0
    if y > 0.0: y = 0.0
    
    # print("x: " + str(x))
    # print("y: " + str(y))
    # print("z: " + str(z))
    # map acc range to octave + 1 range, ex. C4-C5
    xMapped = mapValue(x, -1.0, 0.1, 0, 9)
    yMapped = mapValue(y, -1.0, 0.0, 9, 0)
    # zMapped = 0 # $$$ come back to this if need more accel input

    if offChordLock: 
        # if off chord locked, only play odd scale degrees
        if xMapped % 2 == 0: xMapped += 1
    
    else: 
        # if on chord locked, only play even scale degrees
        if xMapped % 2 == 1: xMapped += 1

    # x
    octaveX = (xMapped // 8) + 4
    scaleDegree = xMapped % 8
    pitchX = scaleOfChords[scaleDegree] + scaleOfChordsRoot + (octaveX * OCTAVE)

    # y
    octaveY = (yMapped // 8) + 5
    scaleDegree = yMapped % 8
    pitchY = scaleOfChords[scaleDegree] + scaleOfChordsRoot + (octaveY * OCTAVE)
    
    # print("Input Pitch: " + str(pitchX))
    return [pitchX, pitchY]

# fill in the middle of contrary motion chords, take a note - skip a note
def contraryMotion(contraryPitch):
    global pivotPitch, scaleOfChords, scaleOfChordsRoot
    chord = []
    # print("\nPivot pitch: " + str(pivotPitch))
    # print("Contrary pitch: " + str(contraryPitch))

    # If playing the pivot pitch, play one note
    if contraryPitch >= pivotPitch:
        chord.append(pivotPitch)
        return chord

    # Map pitches to a pitch class (0 to 11),
    # adjusted to make "0" represent the scale root
    inputPitchClass  = (contraryPitch - scaleOfChordsRoot) % OCTAVE
    pivotPitchClass = (pivotPitch - scaleOfChordsRoot) % OCTAVE

    inputOctave = contraryPitch // OCTAVE # the MIDI octave of the input note
    currentOctave = inputOctave
    octaveSpread = (abs(contraryPitch - pivotPitch)) // OCTAVE # how many octaves apart are the input and pivot pitches?
    inputScaleDegree = scaleOfChords.index(inputPitchClass) # the scale degree of the input note (0-7)
    pivotScaleDegree = scaleOfChords.index(pivotPitchClass) # the scale degree of the pivot note (0-7)
    previousPitch = contraryPitch

    # How many notes should be in the chord?
    chordWidth = 1 + ((pivotScaleDegree - inputScaleDegree) % 8) + (8 * octaveSpread)

    #max chord size is double octave chord so oblique motion works
    chordWidth = min(chordWidth, 9)
    
    # chord voicings by width
    octaveChord = 5
    drop2 = 6
    drop3 = 7
    drop2and4 = 8
    doubleOctaveChord = 9

    # Fill in the chord list by taking a note, skipping a note, taking a note...
    # until the desired chord width is achieved
    contrary = 0 # used for iteration to build the polyphony
    for note in range(1, chordWidth+1):
        currentPitch = scaleOfChords[(inputScaleDegree + contrary) % 8] + scaleOfChordsRoot + (OCTAVE * (currentOctave - 1))
        
        # Keep adding higher notes
        if currentPitch < previousPitch:
            currentOctave += 1
            currentPitch += OCTAVE
        
        contrary += 2
        previousPitch = currentPitch
        
        # maintain 4 voices
        if (chordWidth == octaveChord and note == 3) or\
        (chordWidth == drop2 and note in (2, 5) ) or\
        (chordWidth == drop3 and note in (2, 3, 5) ) or\
        (chordWidth == drop2and4 and note in (2, 4, 5, 7) ) or\
        (chordWidth == doubleOctaveChord and note in (2, 3, 5, 7, 8)): 
            continue
    
        # Add a pitch to the chord
        chord.append(currentPitch)

    # Return the complete chord 
    return chord

# keep the bottom note the same, while moving the notes above
def obliqueMotion(inputPitch):
    # redundant, but named differently for clarity
    # may add more functionality to obliqueMotion later on
    setPivotPitch(inputPitch)

# display and play the chord!
def playChord(chord):
    volume, chordChannel = 127, 0
    Play.allNotesOff()
    Play.setVolume(127)
    
    for note in chord:
        note += TRANSPOSE_KEY_SEMITONES  #TODO:bandage
        Play.noteOn(note, volume, chordChannel)

# change the chord scale TODO: this was not working for some reason with iteration ***
def setScaleOfChords(newScaleOfChords):
    global scaleOfChords
    scaleOfChords = newScaleOfChords

# change the root note of the chord scale
def setScaleOfChordsRoot(newRoot):
    global scaleOfChordsRoot
    scaleOfChordsRoot = newRoot

# Change the pivot pitch
def setPivotPitch(newPivotPitch):
    global pivotPitch
    pivotPitch = newPivotPitch   

# Play a bass note for the chord numeral
def toggleBassNote(bassNote, onOrOff):
    volume, channel = 100, 1 
    bassNote += TRANSPOSE_KEY_SEMITONES

    if onOrOff == 1.0:
        # print("Bass note: " + str(bassNote))
        Play.noteOn(bassNote, volume, channel)
    elif onOrOff == 0.0:
        bassNoteOn = True
        while bassNoteOn:
            try: Play.noteOff(bassNote, channel)
            except: bassNoteOn = False

# Play the appropriate chord from a touch input
def handleTouchInput(message):
    global chordNumeralToButtonNameDict, buttonsHeld, accelerometerValues, lastChord, bassNote

    address = message.getAddress()
    arguments = message.getArguments()
    onOrOff = arguments[0]         
    buttonName = str(address[-2] + address[-1]) # we identify the touch OSC button names by the last two characters
    currentChordNumeral = chordNumeralToButtonNameDict.get(buttonName)

    buttonOperations(buttonName)
    
    # if releasing a button, stop all sounds. this allows for touch to hold sustain notes on certain instruments, such as SQUARE
    if onOrOff == 0: 
        buttonsHeld -= 1
        if buttonsHeld == 0:
            if DECAY: decayTimer.start() # turn volume down on a repeating timer, achieves decay effect
            if BASS: toggleBassNote(bassNote, onOrOff)
        return
    else:
        buttonsHeld += 1
        if DECAY: decayTimer.stop()
        

    try: 
        x, y, z = accelerometerValues
    except:
        print("\nTurn on the accelerometer in TouchOSC!!!\nSettings -> Options -> OSC -> Accelerometer (/accxyz)")
        sys.exit(1)

    if  (-1.0 < x < 1.0) and (-1.0 < y < 1.0): 
        pitchX, pitchY = mapAccelerometerToPitch(x, y, z)
    
    try : obliqueMotion(pitchY)
    except: NotImplemented
    
    try: chord = contraryMotion(pitchX)
    except: chord = lastChord
    
    # play the appropriate chord
    lastChord = chord
    playChord(chord)
    if BASS: toggleBassNote(bassNote, onOrOff)
    # print("Chord: " + str(chord))

# Update global variables based on what button was pressed
def buttonOperations(buttonName):
    global KEY, offChordLock, alternate, dominant, familyUp, familyDown, familyAcross, chordNumeral, bassNote
    offChordLock = False      

    # Handle modifier buttons
    if buttonName == "10":   # On Chord lock
        resetFamilyTransformations() 
        if alternate or dominant: 
            makeDefault(chordNumeral)
    elif buttonName == "h6": # Off Chord lock
        offChordLock = True
    elif buttonName == "14": # "Alt" button
        resetFamilyTransformations()
        if not alternate: 
            makeAlternate(chordNumeral)
            alternate = True
    elif buttonName == "h2": # "Make Dominant" Button, turns any chord into a Dom7
        makeDominant()
    elif buttonName == "h5": # Family Down / "Sister" Button, transform down a minor third
        if familyUp: 
            makeFamilyDown()
            familyUp = False
        if familyAcross: 
            makeFamilyAcross()
            familyAcross = False
        if alternate or dominant: 
            makeDefault(chordNumeral)
        if not familyDown: 
            makeFamilyDown()
            familyDown = True # Call helper function
    elif buttonName == "h9": # Family Across / "Cousin" Button, transform across a tritone
        if familyUp: 
            makeFamilyDown()
            familyUp = False
        if familyDown: 
            makeFamilyUp()
            familyDown = False
        if alternate or dominant: 
            makeDefault(chordNumeral)
        if not familyAcross: 
            makeFamilyAcross()
            familyAcross = True
    elif buttonName == "13": # "Family Up / Brother" Button, transform up minor third
        if familyAcross:
            makeFamilyAcross()
            familyAcross = False
        if familyDown: 
            makeFamilyUp()
            familyDown = False
        if alternate or dominant: 
            makeDefault(chordNumeral)
        if not familyUp: 
            makeFamilyUp()
            familyUp = True
    else:
        handleChordNumerals(buttonName)  # Call the function to handle chord numerals

# Reset family transformations
def resetFamilyTransformations():
    global familyUp, familyDown, familyAcross
    
    if familyUp:
        makeFamilyDown()
        familyUp = False
    if familyDown:
        makeFamilyUp()
        familyDown = False
    if familyAcross:
        makeFamilyAcross()
        familyAcross = False

# Chord numeral buttons logic
def handleChordNumerals(buttonName):
    global chordNumeral, bassNote, offChordLock

    resetFamilyTransformations()
    # Set offChordLock to False
    offChordLock = False

    # Logic for setting chord numerals and bass notes
    if buttonName == "16":  # 1 chord
        chordNumeral = 1
        bassNote = KEY[0] + BASS_OCTAVE_OFFSET
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot( KEY[0] )
    elif buttonName == "12":  # 2 chord
        chordNumeral = 2
        bassNote = KEY[1] + BASS_OCTAVE_OFFSET
        setScaleOfChords(MINOR_SEVENTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot( KEY[1] )
    elif buttonName == "h8":  # 3 chord
        chordNumeral = 3
        bassNote = KEY[2] + BASS_OCTAVE_OFFSET
        setScaleOfChords(MINOR_SEVENTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot( KEY[2] )
    elif buttonName == "h4":  # 4 chord
        chordNumeral = 4
        bassNote = KEY[3] + BASS_OCTAVE_OFFSET
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot( KEY[3] )
    elif buttonName == "15":  # 5 chord
        chordNumeral = 5
        bassNote = KEY[4] + BASS_OCTAVE_OFFSET
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot( KEY[4] )
    elif buttonName == "11":  # 6 chord
        chordNumeral = 6
        bassNote = KEY[5] + BASS_OCTAVE_OFFSET
        setScaleOfChords(MINOR_SEVENTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot( KEY[5] )
    elif buttonName == "h7":  # 7 chord
        chordNumeral = 7
        bassNote = KEY[6] + BASS_OCTAVE_OFFSET
        setScaleOfChords(MINOR_SEVENTH_FLAT_FIVE_DIMINISHED_SCALE)
        setScaleOfChordsRoot( KEY[6] )
    elif buttonName == "h3":  # 1 chord + 1 octave, aka 8 chord
        chordNumeral = 8
        bassNote = KEY[0] + BASS_OCTAVE_OFFSET + OCTAVE
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot( KEY[0] + OCTAVE )
    
    return True

# Switch to an alternate scale of chords based on the current chord numeral
def makeAlternate(chordNumeral):
    global KEY, alternate
    # print("\nAlt scale of chords")

    if chordNumeral in [1, 8]: # 1 chord alt
        # the major 6th on the 5
        # Ex: Cmaj6 --> Gmaj6/C (Cmaj9)
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH)
        setScaleOfChordsRoot( KEY[1] )
    elif chordNumeral == 2: # 2 chord alt
        # Ex: Dmin7 --> Cmaj6/D (Dmin11)
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD)
        setScaleOfChordsRoot( KEY[2] )
    elif chordNumeral == 3: # 3 chord alt
        # Ex: Emin7 --> Cmaj6/E
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD)
        setScaleOfChordsRoot( KEY[2] )
    elif chordNumeral == 4: # 4 chord alt
        # Ex: Fmaj6dim --> Cmaj6dim/F (Fmaj9)
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH)
        setScaleOfChordsRoot( KEY[4] )
    elif chordNumeral == 5: # 5 chord alt
        # minor 6th on the 5
        # Ex: G7dim --> Dmin6dim/G
        setScaleOfChords(MINOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH)
        setScaleOfChordsRoot( KEY[5] )
    elif chordNumeral == 6:
        # Ex: Amin7 --> Gmaj6/A (Amin11)
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD)
        setScaleOfChordsRoot( KEY[6] )
    elif chordNumeral == 7:
        # Ex: Bmin7b5 --> G7/B
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_THIRD)
        setScaleOfChordsRoot( KEY[6] )

    alternate = True

# Make current scale of chords a dominant seventh diminished scale with the same root
def makeDominant():
    global dominant
    setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE)
    dominant = True

# Switch to family a minor third up
def makeFamilyUp():
    global scaleOfChords, scaleOfChordsRoot
    # bass note of scale of chords goes down in cycle through 1 - 3 - 5 - 6/7, for voice leading
    # scale of chords goes ups in minor thirds
    # ex: Dmin6 --> Fmin6/D

    # maj6 variants
    if scaleOfChords == MAJOR_SIXTH_DIMINISHED_SCALE:
        setScaleOfChords(MINOR_SEVENTH_DIMINISHED_SCALE)
    elif scaleOfChords == MAJOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD:
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot(scaleOfChordsRoot - 1)
    elif scaleOfChords == MAJOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH:
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD)
    elif scaleOfChords == MINOR_SEVENTH_DIMINISHED_SCALE:
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH)
        setScaleOfChordsRoot(scaleOfChordsRoot + 1)
    # min6 variants
    elif scaleOfChords == MINOR_SIXTH_DIMINISHED_SCALE:
        setScaleOfChords(MINOR_SEVENTH_FLAT_FIVE_DIMINISHED_SCALE)
    elif scaleOfChords == MINOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD:
        setScaleOfChords(MINOR_SIXTH_DIMINISHED_SCALE)
    elif scaleOfChords == MINOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH:
        setScaleOfChords(MINOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD)
        setScaleOfChordsRoot(scaleOfChordsRoot - 1)
    elif scaleOfChords == MINOR_SEVENTH_FLAT_FIVE_DIMINISHED_SCALE:
        setScaleOfChords(MINOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH)
        setScaleOfChordsRoot(scaleOfChordsRoot + 1)
    # dom7 variants
    elif scaleOfChords == DOMINANT_SEVENTH_DIMINISHED_SCALE:
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_SEVENTH)
        setScaleOfChordsRoot(scaleOfChordsRoot + 1)
    elif scaleOfChords == DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_THIRD:
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot(scaleOfChordsRoot - 1)
    elif scaleOfChords == DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_FIFTH:
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_THIRD)
    elif scaleOfChords == DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_SEVENTH:
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_FIFTH)
    
    familyUp = True

# Switch to family a minor third down
def makeFamilyDown():
    global scaleOfChords, scaleOfChordsRoot
    # bass note of scale of chords goes up in cycle through 1 - 3 - 5 - 6/7, for voice leading
    # scale of chords goes down in minor thirds
    # ex: Dmin6 --> Bmin6/D

    # maj6 variants
    if scaleOfChords == MAJOR_SIXTH_DIMINISHED_SCALE:
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD)
        setScaleOfChordsRoot(scaleOfChordsRoot + 1)
    elif scaleOfChords == MAJOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD:
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH)
    elif scaleOfChords == MAJOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH:
        setScaleOfChords(MINOR_SEVENTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot(scaleOfChordsRoot - 1)
    elif scaleOfChords == MINOR_SEVENTH_DIMINISHED_SCALE:
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE)
    # min6 variants
    elif scaleOfChords == MINOR_SIXTH_DIMINISHED_SCALE:
        setScaleOfChords(MINOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD)
    elif scaleOfChords == MINOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD:
        setScaleOfChords(MINOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH)
        setScaleOfChordsRoot(scaleOfChordsRoot + 1)
    elif scaleOfChords == MINOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH:
        setScaleOfChords(MINOR_SEVENTH_FLAT_FIVE_DIMINISHED_SCALE)
        setScaleOfChordsRoot(scaleOfChordsRoot - 1)
    elif scaleOfChords == MINOR_SEVENTH_FLAT_FIVE_DIMINISHED_SCALE:
        setScaleOfChords(MINOR_SIXTH_DIMINISHED_SCALE)
    # dom7 variants
    elif scaleOfChords == DOMINANT_SEVENTH_DIMINISHED_SCALE:
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_THIRD)
        setScaleOfChordsRoot(scaleOfChordsRoot + 1)
    elif scaleOfChords == DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_THIRD:
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_FIFTH)
    elif scaleOfChords == DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_FIFTH:
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_SEVENTH)
    elif scaleOfChords == DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_SEVENTH:
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot(scaleOfChordsRoot - 1)

    familyDown = True

# Switch to family a tritone across
def makeFamilyAcross():
    global scaleOfChords, scaleOfChordsRoot
    # bass note of scale of chords go between 1 - 5  or 3 - 6/7, for voice leading
    # scale of chords goes across in tritones
    # ex: Dmin6 --> Abmin6/Eb

    # maj6 variants
    if scaleOfChords == MAJOR_SIXTH_DIMINISHED_SCALE:
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH)
        setScaleOfChordsRoot(scaleOfChordsRoot + 1)
    elif scaleOfChords == MAJOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD:
        setScaleOfChords(MINOR_SEVENTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot(scaleOfChordsRoot - 1)
    elif scaleOfChords == MAJOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH:
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot(scaleOfChordsRoot - 1)
    elif scaleOfChords == MINOR_SEVENTH_DIMINISHED_SCALE:
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD)
        setScaleOfChordsRoot(scaleOfChordsRoot + 1)
    # min6 variants
    elif scaleOfChords == MINOR_SIXTH_DIMINISHED_SCALE:
        setScaleOfChords(MINOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH)
        setScaleOfChordsRoot(scaleOfChordsRoot + 1)
    elif scaleOfChords == MINOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD:
        setScaleOfChords(MINOR_SEVENTH_FLAT_FIVE_DIMINISHED_SCALE)
    elif scaleOfChords == MINOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH:
        setScaleOfChords(MINOR_SIXTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot(scaleOfChordsRoot - 1)
    elif scaleOfChords == MINOR_SEVENTH_FLAT_FIVE_DIMINISHED_SCALE:
        setScaleOfChords(MINOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD)
    # dom7 variants
    elif scaleOfChords == DOMINANT_SEVENTH_DIMINISHED_SCALE:
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_FIFTH)
        setScaleOfChordsRoot(scaleOfChordsRoot + 1)
    elif scaleOfChords == DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_THIRD:
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_SEVENTH)
    elif scaleOfChords == DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_FIFTH:
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot(scaleOfChordsRoot - 1)
    elif scaleOfChords == DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_SEVENTH:
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_THIRD)

    familyAcross = True

# Reset to default scale of chords for the current chord numeral
def makeDefault(chordNumeral):
    global alternate, dominant
    alternate = False
    dominant = False
    buttonName = chordNumeralToButtonNameDict.get(chordNumeral)
    buttonOperations(buttonName)
# endregion

# region OSC and MIDI Setup
oscIn = OscIn( OSC_LISTENER_PORT )  
oscIn.hideMessages()
oscIn.onInput("/7/push.*", handleTouchInput) 
oscIn.onInput("/accxyz", parseAccelerometerData) 
# endregion

# region ASCII Art and Intro Message
ascii_art = """
 __  __ _   _  ____ 
|  \/  | \ | |/ ___| 
| |\/| |  \| | |     
| |  | | |\  | |___  
|_|  |_|_| \_|\____| 
"""

print(ascii_art)
print("\"You know... Coleman Hawkins, when I worked with him,\n" +  
        "he told me \'I don't play chords, I play movements.\'\n" +
        "I understand it now.\" - Barry Harris\n")
print("Play movements, not chords!")
# endregion

# region Changelog
# 11.16.24:
# Added global transpose, bass, and decay settings. Cleaned up octave logic.
# Refactored buttonOperations() with clearer helper functions.
#
# 7.30.24:
# Chords only play when tapped. Limited to 4 voices for polyphonic clarity. 
# When switching to a different chord, always locks to on chord. Bass note plays for chord button.
# Contrary motion on roll, and oblique motion (holding bottom note) on pitch.
# Separated buttonOperations into its own function to clean up handleTouchInputs.
# Alternate scale of chords button added. "Make Dominant" button Added.
# Family up, down, and across added.
# endregion