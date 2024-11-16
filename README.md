# Movements, Not Chords

This program is a smartphone instrument for polyphonic motion. By tapping the screen and tilting your phone, you can play beautiful polyphonic movements in contrary and oblique motion. Such fluid harmony takes a lifetime to master on traditional instruments.

Using 8 note "scales of chords", contrary motion can be done indefinitely, alternating between an "on" and "off" chord. The "off" chord is always a diminished seventh, and the "on" chord consists of a combination of notes from the other two possible diminished chords. "On" chords of the same type, that share the same "off" chord, are family!

To learn more about this **beautiful** theory of music, research Dr. Barry Harris - a master Bebop pianist and educator. Here's a super succinct summary of his "Creation Theory": https://www.youtube.com/shorts/OmWSgjwroLM

This prototype uses JythonMusic and the TouchOSC app on a smartphone. I intend to create a mobile app using JUCE to achieve minimal playback latency, and a more ergonomic button layout.

## Setup JythonMusic

- https://jythonmusic.me/download-3/

## Setup mnc.py

- Look under the USER SETTINGS header and adjust the constants as desired
- Set the OSC_LISTENER_PORT to an available port
- Choose MIDI sounds

## Setup the TouchOSC Mobile App

### Settings -> Connections -> OSC

- Set "Host" to match the IP address of the machine running mnc.py  
- Set "Port(outgoing)" to match OSC_LISTENER_PORT in mnc.py

### Settings -> Layout

- Select "LiveControl iPad" (even if using smartphone)

### Settings -> Options -> OSC

- Enable "Accelerometer (/accxyz)"

### Navigate to Page 6 of "Live Control iPad"

- You should see an array or 16 red squares, these are the relevant buttons

## How to **Play** the Instrument

### Hand Movements = Harmonic Movements!

1. Hold your phone in portrait mode with your dominant hand.
2. Start with the phone **perpendicular to the ground.**
    1. This should play one note (the root note of the current chord).
3. Now, imagine there is **water on the surface of your screen.**
4. Slowly pour the water off the left edge of your phone.
    1. This achieves **contrary motion!**
    2. One note moves up while another moves down.
    3. Gaps are filled in between the outermost notes to play 1 -> 4 note voicings.
5. Slowly pour the water off the screen towards your chest. *Or, it may be more intuitive to think of lifting the camera end of your phone to the sky.*
    1. This achieves **oblique motion!**
    2. The lowest note stays the same, and the 3 notes above it move up and down together.
6. Experiment with combinations of these "roll" and "pitch" orientation changes.

## Tap the Screen to Change Chord Numerals and Modify "Scales of Chords"

- Tap buttons with your non-dominant hand
- The bottom 8 squares change between the chords of a traditional major key
- The top 8 squares are modifiers that work well with the current chord numeral
  - The "On Chord" button plays the most recently tapped chord numeral
  - The "Off Chord" button plays a tense chord that resolves beautifully back to the "on" chord (*or any of the other modifiers!*)
  - The "Make Dominant" button turns any chord into a dominant 7th to propel harmonic movement
  - The "Pretty Subtitution" button gives on of my preferred substitutions
  - The "Sister, Cousin, and Brother Chords" are the family of the "on" chord. They represent chords of the same type with roots minor thirds apart. These family chords all share the same "off" chord. Try moving between them through the "off" chord!

## Prototype Interface

![Alt text](interface_prototype.jpg?raw=true)
