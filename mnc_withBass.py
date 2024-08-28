# mnc_withBass.py
# Movements, Not Chords
#
# This program is an instrument, intended to be played with the TouchOSC mobile app on a smartphone.
# Using 8 note "scales of chords", contrary motion can be done indefinitely,
# alternating between an "on" and "off" chord. The "off" chord is always a diminished seventh,
# and the "on" chord consists of a combination of notes from the other two possible diminished chords.
# "On" chords of the same type, that share the same "off" chord, are family!
#
# region Changelog
# 7.30.24:
# Chords only play when tapped. Limited to 4 voices for polyphonic clarity. 
# When switching to a different chord, always locks to on chord. Bass note plays for chord button.
# Contrary motion on roll, and oblique motion (holding bottom note) on pitch.
# Separated buttonOperations into its own function to clean up handleTouchInputs.
# Alternate scale of chords button added. "Make Dominant" button Added.
# Family up, down, and across added.
#
# 
# endregion

from midi import *
from music import *
from osc import *
from timer import *

# region Global Variables

# region Scales of Chords
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
# endregion

key = MAJOR_SCALE # 7 note scales, different from the "scales of chords". Used to follow typical chord progression notations.
keyRoot = C_1 # the root of the 7 note home scale
scaleOfChords = MAJOR_SIXTH_DIMINISHED_SCALE # choose a chord scale to move through
scaleOfChordsRoot = C_1 # the root of the scale of chords
pivotPitch = C4 # the note around which the contrary motion expands/shrinks
                # if the pivot pitch is played, only that single pitch will sound
bassNote = C3
keysPressed = 0
buttonsHeld = 0
lastButtonPressed = ""
lastChord = []
chordNumeral = 1
onChordLock = False
offChordLock = False
alternate = False # alternate scale of chords for each chord numeral in the key
dominant = False
familyUp = False
familyDown = False
familyAcross = False
eightChord = False
accelerometerValues = []

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
# endregion

# region Functions
# turn volume down on a repeating timer, achieves decay effect
def decay(channel):
    global decayTimer
    currentVolume = Play.getVolume(channel)
    newVolume = currentVolume - 3

    if newVolume == 0: 
        decayTimer.stop()
        Play.allNotesOff()
        return
    
    Play.setVolume(newVolume)

decayTimer = Timer(1, decay, [0], True) 

# Parse accelerometer data from OSC messages
accOSCIncrement = 0
def parseAccelerometerData(message):
    global accOSCIncrement, accelerometerValues

    # accOSCMod = 4 # change sensitivity of acc
    # accOSCIncrement = (accOSCIncrement + 1) % accOSCMod
    # if accOSCIncrement % accOSCMod != 0: return

    address = message.getAddress()
    accelerometerValues = message.getArguments()


# Map accelerometer values to pitches
def mapAccelerometerToPitch(x, y, z):
    global scaleOfChords, scaleOfChordsRoot, onChordLock, offChordLock, keyRoot

    # Ensure x and y are within range
    if x > 0: x = 0.0
    if y > 0: y = 0.0

    if z > 1:
        x = 0.0
        y = 0.0
        # print("z > 1")
    elif z > 0 : 
        x = -1.0
        y = -1.0
        # print("z > 0")
    
    # map acc range to two octave range (17 notes), ex. C3-C5
    xMapped = mapValue(x, -1.0, 1.0, 0, 16)
    yMapped = mapValue(y, -1.0, 1.0, 16, 0)
    zMapped = 0 # $$$ come back to this if need more accel input

    # if on chord locked, only play even scale degrees
    if onChordLock and xMapped % 2 == 1:
        xMapped += 1
    # if off chord locked, only play odd scale degrees
    elif offChordLock and xMapped % 2 == 0:
        xMapped += 1

    # stay within the two octave range
    xMapped %= 16
    yMapped %= 16

    # x
    octaveX = (xMapped // 8) + 4
    scaleDegree = xMapped % 8
    pitchX = scaleOfChords[scaleDegree] + scaleOfChordsRoot + (octaveX * 12)
    if scaleOfChordsRoot < keyRoot:
        pitchX += 12

    # y
    octaveY = ((yMapped + 1) // 9) + 4
    scaleDegree = yMapped % 8
    pitchY = scaleOfChords[scaleDegree] + scaleOfChordsRoot + (octaveY * 12)

    # # z
    # octaveZ = (zMapped // 8) + 4
    # scaleDegree = zMapped % 8
    # pitchZ = scaleOfChords[scaleDegree] + scaleOfChordsRoot + (octave * 12)
    # if scaleOfChordsRoot < keyRoot:
    #     pitchZ += 12
    
    # print("Input Pitch: " + str(pitchX))
    return [pitchX, pitchY]


# fill in the middle of contrary motion chords, take a note - skip a note
def contraryMotion(inputPitch):
    global pivotPitch, scaleOfChords, scaleOfChordsRoot
    chord = []

    # If playing the pivot pitch, play one note
    if inputPitch == pivotPitch:
        chord.append(inputPitch)
        return chord

    # Map pitches to a pitch class (0 to 11),
    # adjusted to make "0" represent the scale root
    inputPitchClass  = (inputPitch - scaleOfChordsRoot) % 12
    pivotPitchClass = (pivotPitch - scaleOfChordsRoot) % 12

    # print("\nPivot pitch: " + str(pivotPitch))
    # print("Contrary pitch: " + str(inputPitch))

    # # If input note is outside of the selected chord scale, play one note
    # if inputPitchClass not in scaleOfChords:
    #     chord.append(inputPitch)
    #     return chord

    inputOctave = inputPitch // 12 # the MIDI octave of the input note
    currentOctave = inputOctave
    octaveSpread = (abs(inputPitch - pivotPitch)) // 12 # how many octaves apart are the input and pivot pitches?
    inputScaleDegree = scaleOfChords.index(inputPitchClass) # the scale degree of the input note (0-7)
    pivotScaleDegree = scaleOfChords.index(pivotPitchClass) # the scale degree of the pivot note (0-7)
    previousPitch = inputPitch

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
        currentPitch = scaleOfChords[(inputScaleDegree + contrary) % 8] + scaleOfChordsRoot + (12 * (currentOctave - 1))
        
        # Keep adding higher notes
        if currentPitch < previousPitch:
            currentOctave += 1
            currentPitch += 12
        
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
        Play.noteOn(note, volume, chordChannel)


# change the chord scale TODO: this was not working for some reason with iteration ***
def setScaleOfChords(newScaleOfChords):
    global scaleOfChords
    scaleOfChords = newScaleOfChords


# change the root note of the chord scale
def setScaleOfChordsRoot(newRoot):
    global scaleOfChordsRoot
    scaleOfChordsRoot = newRoot


# change the pivot pitch
def setPivotPitch(newPivotPitch):
    global pivotPitch
    pivotPitch = newPivotPitch   


# plays a bass note for the chord numeral
def toggleBassNote(bassNote, onOrOff):
    volume, channel = 100, 1 

    if onOrOff == 1.0:
        # print("Bass note: " + str(bassNote))
        Play.noteOn(bassNote, volume, channel)
    elif onOrOff == 0.0:
        bassNoteOn = True
        while bassNoteOn:
            try: Play.noteOff(bassNote, channel)
            except: bassNoteOn = False


# play the appropriate chord from a touch input
def handleTouchInput(message):
    global chordNumeralToButtonNameDict, buttonsHeld, accelerometerValues, decayTimer, eightChord, lastChord, bassNote

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
            decayTimer.start() # turn volume down on a repeating timer, achieves decay effect
            toggleBassNote(bassNote, onOrOff)
        return
    else:
        buttonsHeld += 1
        decayTimer.stop()
        

    x, y, z = accelerometerValues
    if  (-1.0 < x < 1.0) and (-1.0 < y < 1.0): 
        pitchX, pitchY = mapAccelerometerToPitch(x, y, z)

    # if 8chord (1chord), raise x input pitch by an octave
    if eightChord: 
        try: pitchX += 12
        except: None

        try: pitchY += 12
        except: None
    
    try: obliqueMotion(pitchY)
    except: pitchY = 0

    try: chord = contraryMotion(pitchX)
    except: chord = lastChord
    
    # play the appropriate chord
    lastChord = chord
    playChord(chord)
    toggleBassNote(bassNote, onOrOff)
    # print("Chord: " + str(chord))


# update global variables based on what button was pressed
def buttonOperations(buttonName):
    global MAJOR_SIXTH_DIMINISHED_SCALE, MINOR_SIXTH_DIMINISHED_SCALE, DOMINANT_SEVENTH_FLAT_FIVE_DIMINISHED_SCALE
    global key, keyRoot, onChordLock, offChordLock, alternate, dominant, familyUp, familyDown, familyAcross, lastButtonPressed, chordNumeral, eightChord, bassNote

    bassRange = keyRoot + (12 * 2)
    pivotRange = keyRoot + (12 * 4)
    onChordLock = False
    offChordLock = False      

    # modifier buttons
    if buttonName == "10": # On Chord Lock  
        onChordLock = True
        if familyUp:
            makeFamilyDown()
            familyUp = False
        if familyDown:
            makeFamilyUp()
            familyDown = False
        if familyAcross:
            makeFamilyAcross()
            familyAcross = False
        if alternate or dominant:
            makeDefault(chordNumeral)
            alternate = False
            dominant = False
            onChordLock = True
    elif buttonName == "h6": # Off Chord Lock
        offChordLock = True
    elif buttonName == "14": # "Alt" button
        onChordLock = True
        if familyAcross: 
            makeFamilyAcross()
            familyAcross = False
        if familyDown: 
            makeFamilyUp()
            familyDown = False
        if familyUp: 
            makeFamilyDown()
            familyDown = False
        if not alternate: 
            makeAlternate(chordNumeral)
            alternate = True
    elif buttonName == "h2": # "Make Dominant" Button, turns any chord into a Dom7
        onChordLock = True
        makeDominant()
    elif buttonName == "13": # "Family Up / Brother" Button, transform up minor third
        onChordLock = True
        if familyAcross:
            makeFamilyAcross()
            familyAcross = False
        if familyDown: 
            makeFamilyUp()
            familyDown = False
        if alternate or dominant: 
            makeDefault(chordNumeral)
            alternate = False
            dominant = False
            onChordLock = True
        if not familyUp: 
            makeFamilyUp()
            familyUp = True
    elif buttonName == "h9": # Family Across / "Cousin" Button, transform across a tritone
        onChordLock = True
        if familyUp: 
            makeFamilyDown()
            familyUp = False
        if familyDown: 
            makeFamilyUp()
            familyDown = False
        if alternate or dominant: 
            makeDefault(chordNumeral)
            alternate = False
            dominant = False
            onChordLock = True
        if not familyAcross: 
            makeFamilyAcross()
            familyAcross = True
    elif buttonName == "h5": # Family Down / "Sister" Button, transform down a minor third
        onChordLock = True
        if familyUp: 
            makeFamilyDown()
            familyUp = False
        if familyAcross: 
            makeFamilyAcross()
            familyAcross = False
        if not familyDown: 
            makeFamilyDown()
            familyDown = True
    elif buttonName == lastButtonPressed: # if the button is the same and also a chord button, we don't need to change anything
        return
    else:
        if familyAcross: 
            makeFamilyAcross()
            familyAcross = False
        if familyDown: 
            makeFamilyUp()
            familyDown = False
        if familyUp: 
            makeFamilyDown()
            familyDown = False
        if  alternate or dominant: 
            alternate = False
            dominant = False
            makeDefault(chordNumeral)
            

        for b in [familyDown, familyUp, familyAcross, alternate]: b = False
        
    # chord buttons
    if buttonName == "16": # 1 chord
        chordNumeral = 1
        bassNote = key[0] + bassRange
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot(key[0] + keyRoot)
        eightChord = False
    elif buttonName == "12": # 2 chord
        chordNumeral = 2
        bassNote = key[1] + bassRange
        setScaleOfChords(MINOR_SEVENTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot((key[1] + keyRoot) % 12)
        eightChord = False
    elif buttonName == "h8": # 3 chord
        chordNumeral = 3
        bassNote = key[2] + bassRange
        setScaleOfChords(MINOR_SEVENTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot((key[2] + keyRoot) % 12)
        eightChord = False
    elif buttonName == "h4": # 4 chord
        chordNumeral = 4
        bassNote = key[3] + bassRange
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot((key[3] + keyRoot) % 12)
        eightChord = False
    elif buttonName == "15": # 5 chord
        chordNumeral = 5
        bassNote = key[4] + bassRange
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot(key[4] + keyRoot)
        eightChord = False
    elif buttonName == "11": # 6 chord
        chordNumeral = 6
        bassNote = key[5] + bassRange
        setScaleOfChords(MINOR_SEVENTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot((key[5] + keyRoot) % 12)
        eightChord = False
    elif buttonName == "h7": # 7 chord
        chordNumeral = 7
        bassNote = key[6] + bassRange
        setScaleOfChords(MINOR_SEVENTH_FLAT_FIVE_DIMINISHED_SCALE)
        setScaleOfChordsRoot((key[6] + keyRoot) % 12)
        eightChord = False
    elif buttonName == "h3": # 1 chord + 1 octave, aka 8 chord
        chordNumeral = 8
        eightChord = True
        bassNote = key[0] + bassRange + 12
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE)
        setScaleOfChordsRoot((key[0] + keyRoot) % 12)
    
    # Whenever we first hit a button, we should hear the "on chord"
    if buttonName not in [lastButtonPressed, "10", "h6"]:
        onChordLock = True
        lastButtonPressed = buttonName
    
    lastButtonPressed = buttonName
    
    return True

# switch to an alternate scale of chords based on the current chord numeral
def makeAlternate(chordNumeral):
    global key, keyRoot
    
    # print("\nAlt scale of chords")

    if chordNumeral in [1, 8]: # 1 chord alt
        # the major 6th on the 5
        # Ex: Cmaj6 --> Gmaj6/C (Cmaj9)
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH)
        setScaleOfChordsRoot(key[1] + keyRoot)
    elif chordNumeral == 2: # 2 chord alt
        # Ex: Dmin7 --> Cmaj6/D (Dmin11)
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD)
        setScaleOfChordsRoot(key[2] + keyRoot)
    elif chordNumeral == 3: # 3 chord alt
        # Ex: Emin7 --> Cmaj6/E
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD)
        setScaleOfChordsRoot(key[2] + keyRoot)
    elif chordNumeral == 4: # 4 chord alt
        # Ex: Fmaj6dim --> Cmaj6dim/F (Fmaj9)
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH)
        setScaleOfChordsRoot(key[4] + keyRoot)
    elif chordNumeral == 5: # 5 chord alt
        # minor 6th on the 5
        # Ex: G7dim --> Dmin6dim/G
        setScaleOfChords(MINOR_SIXTH_DIMINISHED_SCALE_FROM_FIFTH)
        setScaleOfChordsRoot(key[5] + keyRoot)
    elif chordNumeral == 6:
        # dominant 6 chord sound
        # Ex: Amin7 --> Gmaj6/A (Amin11)
        setScaleOfChords(MAJOR_SIXTH_DIMINISHED_SCALE_FROM_THIRD)
        setScaleOfChordsRoot(key[6] + keyRoot)
    elif chordNumeral == 7:
        # Ex: Bmin7b5 --> G7/B
        # BDFA -->CDFA
        setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE_FROM_THIRD)
        setScaleOfChordsRoot(key[6] + keyRoot)


# make the current scale of chords a dominant seventh diminished scale with the same root
def makeDominant():
    global DOMINANT_SEVENTH_DIMINISHED_SCALE
    setScaleOfChords(DOMINANT_SEVENTH_DIMINISHED_SCALE)

# reset the default scale of chords for the current chord numeral
def makeDefault(chordNumeral):
    buttonName = chordNumeralToButtonNameDict.get(chordNumeral)
    buttonOperations(buttonName)

# switch to family a minor third up
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

# switch to family a minor third down
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

# switch to family a tritone across
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
# endregion

# region OSC and MIDI Setup

# Initialize OSC input to receive messages
oscIn = OscIn()
oscIn.hideMessages()

# OSC listeners
oscIn.onInput("/7/push.*", handleTouchInput) 
oscIn.onInput("/accxyz", parseAccelerometerData) 

# Set MIDI Instruments, such as SQUARE, PIANO, MUSIC_BOX, SYNTH_BASS, CONTRABASS
Play.setInstrument(SQUARE, 0) # choose a MIDI instrument
Play.setInstrument(CONTRABASS, 1) # choose bass sound
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
print("\"You know... Coleman Hawkins, when I worked with him, he told me \'I don't play chords, I play movements.\'\n\
I understand it now.\" - Barry Harris\n")
print("Play movements, not chords!")
# endregion