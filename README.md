# NoteBlockVideoMaker
 A Python script to generate a video from note block songs. Uses Python 3.

## Warning
All the code in this project was created as a one-off thing and was NOT meant to be a fully-fledged video making library. Although the license permits you to modify it & use it in your own projects, keep in mind that this is *extremely* bad code, made to work specifically under the circumstances of the resulting video. There are absolutely no guarantees that it will work with other NBS files, although you're welcome to try :)

## About
NBVM uses [pynbs](https://github.com/vberlier/pynbs/) to read notes from [Note Block Studio](https://opennbs.org/) songs, and generate a [HitFilm](https://fxhome.com/hitfilm-express) project consisting of clips placed at specific times and positions. All of this is driven by a support JSON file which determines what videos to load the clips from, what instruments to assign them to and when they should appear in the video.

But why HitFilm? I did try to use `MoviePy` before, but it couldn't handle the sheer amount of clips and would take hours to render 10 seconds of video. Instead, I decided to reverse engineer the HitFilm Project (`.hfp`) files, which use XML, and generate a project file with only the absolutely necessary to make it load properly into HitFilm. This way I could use the reliability of a robust video editor while being able to preview my changes in real time, considering it takes a fraction of a second to generate a XML file as opposed to a video preview. This solution is by no means good, as it requires a separate program installed on the user's machine to work, but it was all I could think of while creating this.

## Usage
NBVM is meant to work with any note block song from Note Block Studio with minimal modification. 

### Concepts
- **Sections:** A section is a portion of a song spanning a certain tick range. Section lengths are always defined in ticks (i.e. the section at the start of the song may be defined from tick 0 to tick 128). Each section determines the size of the clip grid, and what clips and tracks will play during that time, as well as their position and size in the frame.
- **Clips:** A clip is a one-time snippet of a video file that is associated with an instrument. Everytime the instrument that's assigned to this clip plays in a section, this clip will be triggered. They're usually used for drum hits and transitions. Clips may be simple or compound. Simple clips use only a single snippet of the video, while compound clips may use more than one snippet, each being triggered by a different instrument. (e.g. you could have a drum pattern that uses note blocks tuned to different keys, each key showing the player hitting a different note block).
- **Tracks:** A track is similar to a clip, but it is a longer video file that may or may not span the whole length of the song. They're used for melodic instruments and, rather than defining a single part of the video that will always repeat, it works by defining segments, i.e. a certain portion of the video corresponding to each part of the song. Track segments are triggered sequentially (in the order that they were defined in the settings file) by the first note block with the instrument that's assigned to this track in each section of the song. Tracks can be used for anything, from an in-game recording of Open Note Block Studio's visualizers to an audio spectrum generated with external tools. By default only one track may trigger per section, but you may set a track to appear more than once in a segment, defined by `retrigger_time`. If a track is referenced more times than the number of segments defined, it will loop back to the first segment.

### Settings
Below is a breakdown of the JSON structure used by the settings file. Seconds must always be specified as an `int` or `float`, e.g. `10`, `24.2`, `122.879` (corresponds to 2:02.879).

- _The root object._
    - `"input"`: Path to the input song. Must be an `.nbs` file.
    - `"output"`: Path to the output HitFilm project. Must have the extension `.hfp`, and must be opened with HitFilm 14 or newer.
    - `"width"`: Optional. Width of the output video frame. If not specified, defaults to 1920.
    - `"height"`: Optional. Height of the output video frame. If not specified, defaults to 1080.
    - `"trigger_interval"`: A numeric value, in ticks, determining how many empty ticks between two note blocks with the same instrument (in the same section) should be considered a new "part", therefore, trigger a new segment.
    - `"clips"`: An array defining all the clips used in this song.
        - _\<a simple clip object\>_
            - `"source"`: Path to the source video, starting from the `clips` folder.
            - `"instrument"`: Number of the instrument in the song to assign this clip to. i.e. 0=harp, 1=bass, 2=bassdrum. Custom instruments start at 16, so the third custom instrument in the song would be 16 + 3 = 19.
            - `"start"`: Optional. The time at which the clip starts, in seconds. Any video footage before this time will not be used. Defaults to 0, i.e. starts at the beginning of the video.
            - `"attack"`: The time at which the sound should be played. NBVM will make sure this part always appears, and try to fit as much of the start and end of the video around as possible (as allowed by the time span between the previous and next note block with this instrument).
            - `"ignore_consecutive"`: Optional. A boolean determining if note blocks with the same instrument one after the other should trigger a new instance of a clip. Useful when adding a "tail" to a drum hit to boost its effect; avoids the need to remove those blocks manually in the song. Defaults to `false`.
            - `"end"`: Optional. The time at which the clip ends, in seconds. Any video footage after this time will be cut off. If not specified, uses the video file until the end.
        - _\<a compound clip object\>_
            - `"source"`: Path to the source video, starting from the `clips` folder.
            - `"parts"`: List containing all parts that this clip consists of.
            - _\<a single part\>_
                - `"instrument"`: As above.
                - `"start":` As above.
                - `"attack"`: As above.
                - `"end"`: As above.
         - `"tracks"`: An array defining all the tracks used in this song.
             - `"<track_name>"`: Track object containing the data for this track. Its name must be a string defining the name of this track, which will be referenced in the `sections` part.
                 - `"source"`: Path to the source video, starting from the `clips` folder.
                 - `"instrument"`: Number of the instrument in the song to assign this clip to.
                 - `"segments"`: List containing the segments this track is split into. Segments are triggered sequentially in the order they're defined on this list.
                     - _\<a single segment object\>_
                         - `"start"`: The timestamp of the video at which this segment starts, in seconds.
                         - `"end"`: The timestamp of the video at which this segment ends, in seconds. If not provided, uses the video file until the end.
    - `"sections"`: An array defining the sections to be generated from the song file.
        - _\<a single section object\>_
            - `"start"`: The tick at which this segment will start appearing on the video.
            - `"end"`: The tick at which this segment will stop appearing on the video. Must be specified for technical reasons; must not be greater than the start of the next segment.
            - `"grid_size"`: The grid size to split the video frame into while displaying this section. e.g. `4` will make a 4x4 grid.
            - `"clips"`: A list defining the clips and tracks that will appear during this section.
                - _\<a single clip\>_
                    - `"name"`: A string matching the name of a clip defined in `clips` or `tracks`. If both are defined, the clip with that name will be used. If neither are defined, it will be ignored with a console message.
                    - `"size"`: Optional. The size in grid cells that this clip will span in the video frame (e.g. 2 would take 2x2 spaces on the grid). Defaults to 1.
                    - `"pos"`: An array defining the x and y position of the grid cell that this clip should appear at. (e.g. for a `grid_size` of 4, the possible range would go from `[0 , 0]` to `[3, 3]`.
                        - The x position of the grid cell.
                        - The y position of the grid cell.
                    - `"triggers"`: Optional. Determines how many times this clip can be triggered in this section. Defaults to 1. If more than 1, a new segment will be triggered if the number of empty ticks between two note blocks with this track's instrument matches or exceeds the `retrigger_time`, defined at the start.
