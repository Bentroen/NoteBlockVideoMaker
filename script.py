#import moviepy.editor as mpy
import hitfilm
import json
import os
import pynbs
import xml.etree.ElementTree as ET
import uuid


INPUT = "input.nbs"
OUTPUT = "output.mp4"
TRACK = "track.mp3"
WIDTH = 1920
HEIGHT = 1080

DELAY = 0.2


def seconds_to_frames(s, fps=60):
	return int(round(s * 60))

def frames_to_seconds(s, fps=60):
	return s / 60

def setup_clip(filename, name):
	asset = project.add_media(file, name)
	track_id = project.add_track(name=name, type='video')
	return asset, track_id


with open("settings.json") as f:
	config = json.load(f)
	
song = pynbs.read(INPUT)
length = song.header.song_length / song.header.tempo + 1


'''
project = hitfilm.Project()
asset_id = project.add_media("clips/drums/crash.mp4", "Crash")
track = project.add_track("Wood Click")
clip = hitfilm.Clip(track_id, asset_id, start=240, end=280, asset_start=0, posx=0, posy=0, scalex=0, scaley=0, speed=1)
project.add_clip(clip, track_id, asset_id)

project.save("test.hfp")
'''

project = hitfilm.Project()

# Prepare clips for use in the video
clips = {}
for name, clip in config["clips"].items():
	print("Loading clip {}".format(name))
	path = clip["source"]
	instrument = clip["instrument"]
	start = clip.get("start", 0)
	attack = clip.get("attack", 0)
	end = clip.get("end")
	
	file = os.path.join("clips", path)
	asset, track_id = setup_clip(file, name)
	clips[name] = (instrument, start, attack, end, asset, track_id)a
	

# Prepare tracks for use in the video
tracks = {}
for name, track in config["tracks"].items():
	path = track["source"]
	file = os.path.join("clips", path)
	instrument = track["instrument"]
	segments = []
	for i, section in enumerate(track["segments"]):
		print("Loading section {} of track {}".format(i+1, name))
		start = section.get("start", 0)
		end = section.get("end", 60)
		segments.append(clip)
	asset, track_id = setup_clip(file, name)
	tracks[name] = [instrument, 0, asset, track_id]


# Place clips into final video for each section

video = []
last_tick = 0

for section in config["sections"]:

	print("Starting render of section at tick {}".format(start))
	
	section_start = section["start"]
	section_end = section["end"]
	last_tick = section_end
	grid_size = section["grid_size"]
	
	cellw = WIDTH / grid_size
	cellh = HEIGHT / grid_size
	
	for item in section["clips"]:
	
		# Figure out if a clip or a track
		name = item["name"]
		if name in clips:
			ins, start, attack, end, asset, track_id = clips[name]
			type = "clip"
		elif name in tracks:
			ins, current_session, asset, track_id = tracks[name]
			#ins, current_section, segments = tracks[name]
			#clip = segments[current_section]
			type = "track"
			#tracks[name][1] += 1 # increase next segment to be used
		else:
			print("Skipping undefined clip: {}".format(name))
			continue
		
		# Calculate this clip's size and position on the frame
		size = item["size"]
		pos = item["pos"]
		
		x = pos[0] * cellw
		y = pos[1] * cellh
		w = int(cellw * size)
		h = int(cellh * size)
		
		max_time = section_end / song.header.tempo
		
		# Get the clip's appearance times from the notes in song
		chunk = filter(lambda x: x.tick >= section_start and x.tick < section_end, song.notes)
		notes = sorted(filter(lambda y: y.instrument == ins, chunk), key=lambda z: z.tick)
		times = []
		
		if type == "clip":
			previous_tick = None
			for note in notes:
				tick = note.tick
				if tick == previous_tick:
					# skip repeated instruments in the same tick
					continue
				time = tick / song.header.tempo - attack
				#if time + clip.duration >= max_time:
				#	clip = clip.set_end(max_time - time)
				max_time = end
				times.append(time)
				previous_tick = tick
				
		elif type == "track":
			note = notes[0]
			tick = note.tick

			time = tick / song.header.tempo
			print(tick, time)
			times.append(time)
			tracks[name][1] += 1 # increase current section

		
		# Add clip to the video
		for time in times:
			clip = hitfilm.Clip(track_id, asset, time)
			clip.set_position(x, y)
			clip.set_size(w, h)		
			
			project.add_clip(clip)
			
			# TWO OPTIONS HERE: 1) Either make Clip completely independent of the project,
			# and only generate a UUID on project.add_clip(), or require a new instance of
			# Clip everytime a new clip is added.

		print("Rendering instrument {} at tick {}".format(note.instrument, note.tick))


project.save("output.hfp")

'''
length = last_tick / song.header.tempo + 1
audio = mpy.AudioFileClip(TRACK).set_duration(length).set_start(10)



final = mpy.CompositeVideoClip(video, size=(WIDTH, HEIGHT))
#final = final.without_audio().set_audio(final.audio)

final = final.set_audio(audio.set_duration(length))
#final.preview(fps=10)

if False:
	for x in range(int(length)):
		print("Generating preview frame {} of {}".format(x + 1, int(length)))
		final.save_frame("frames/{}.png".format(x), t=x)

final.write_videofile(OUTPUT, fps=60, threads=4, logger='bar', preset='ultrafast')
'''