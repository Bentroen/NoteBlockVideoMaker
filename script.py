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

def ensure_section_time(start, duration, min_time, max_time):
	if start < min_time:
		start = min_time
		duration -= (min_time - start)

	if start + duration >= max_time:
		end = max_time - start
	else:
		end = duration
		
	return start, end

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
	if not end:
		end = asset.duration
	clips[name] = (instrument, start, attack, end, asset, track_id)
	

# Prepare tracks for use in the video
tracks = {}
for name, track in config["tracks"].items():
	path = track["source"]
	file = os.path.join("clips", path)
	instrument = track["instrument"]
	segments = []
	asset, track_id = setup_clip(file, name)
	for i, section in enumerate(track["segments"]):
		print("Loading section {} of track {}".format(i+1, name))
		start = section.get("start", 0)
		end = section.get("end")
		if not end:
			end = asset.duration
		segments.append((start, end))
	tracks[name] = [instrument, 0, asset, track_id, segments]


# Place clips into final video for each section
video = []
last_tick = 0

for section in config["sections"]:

	print("Starting render of section at tick {}".format(start))
	
	section_start = section["start"]
	section_end = section["end"]
	last_tick = section_end
	grid_size = section["grid_size"]
	
	if section_start > song.header.song_length - 1:
		break
	
	cellw = WIDTH / grid_size
	cellh = HEIGHT / grid_size
	
	for item in section["clips"]:
		
		# Figure out if a clip or a track
		name = item["name"]
		if name in clips:
			ins, inpoint, attack, outpoint, asset, track_id = clips[name]
			type = "clip"
		elif name in tracks:
			ins, current_segment, asset, track_id, segments = tracks[name]
			# loop back to the first segment when running out
			if current_segment > len(segments) - 1:
				current_segment = 0
			inpoint, outpoint = segments[current_segment]
			type = "track"
			tracks[name][1] = current_segment + 1 # increase next segment to be used
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
		
		min_time = section_start / song.header.tempo
		max_time = section_end / song.header.tempo
		
		# Get the clip's appearance times from the notes in song
		chunk = filter(lambda x: x.tick >= section_start and x.tick < section_end, song.notes)
		dirty_notes = sorted(filter(lambda y: y.instrument == ins, chunk), key=lambda z: z.tick)
		previous_tick = -1
		notes = dirty_notes
		notes = []
		# remove repeated instruments in the same tick
		for note in dirty_notes:
			if note.tick > previous_tick:
				notes.append(note)
			previous_tick = note.tick
				
		times = []
		
		if type == "clip":
			last_attack = -1
			for i, note in enumerate(notes):
				tick = note.tick
				
				'''
				# find next tick time to figure out how much "margin"
				try:
					next_tick = notes[i + 1].tick
				except IndexError:
					next_tick = 10000
				#######attack_delay = attack - inpoint
				'''
				
				
				
				
				# set clip to start exactly at the attack point
				start = tick / song.header.tempo
				asset_start = attack
				duration = outpoint - attack
				
				print(last_attack, start)
				time_from_last_attack = start - last_attack
				attack_time = attack - inpoint

				# Use 1/4 of the last clip's "release" for the start of
				# the current clip, the time from the start to the attack
				# of the clip, or 1/4 of a second (whatever is smaller).
				advance = min(max(time_from_last_attack / 4, 0), attack_time, 0.25)
				
				choices = [max(time_from_last_attack / 4, 0), attack_time, 0.25]
				print("time from last: {} / attack time: {} / max: {}".format(*choices))
				print("picking: {}".format(min(choices)))
				
				# move clip forward by the calculated start position
				asset_start -= advance
				start -= advance
				duration += advance
				
				# prevent clip from exceeding section time
				#start, asset_start, end = ensure_section_time(start, duration, min_time, max_time)
				start, end = ensure_section_time(start, duration, min_time, max_time)
				
				times.append((start, asset_start, end))
				last_attack = start + attack_time
				
				
				start = tick / song.header.tempo
				timeframe = next_tick / song.header.tempo - start
				advance = min(0.25, timeframe)
				if advance < 0.25:
					asset_start = attack
				else:
					asset_start = attack - 0.25
				print(attack, advance, asset_start)
				start -= advance
				
				# ANOTHER APPROACH: set the minimum clip length to be [attack + min(0.25, timeframe)], subtract it from timeframe and split leftover time into head and tail equally 
				
				# prevent clip from exceeding section time
				duration = outpoint - asset_start
				start, end = ensure_section_time(start, duration, min_time, max_time)
				
				
				# prevent overlapping/wait for attack of previous clip
				delay = 0
				print(last_attack, start)
				#if last_attack and start < last_attack + 0.25:
				#	delay = start - last_attack + 0.25
				if last_attack and start < last_attack:
					delay = last_attack - start
					print(delay)
					duration -= delay
					asset_start += delay
					start += delay
				last_attack = start + duration #start + attack_delay
				
				times.append((start, asset_start, end))
				
				# Center clip around [attack, attack + 0.25] and fit whatever else you can
				# in the range [start, end] around that.
				
		elif type == "track":
			try:
				note = notes[0]
			except IndexError as e:
				raise ValueError("Couldn't add track '{}' on section at tick {}: No note blocks with instrument {} were found".format(name, section_start, ins)) from None
			
			tick = note.tick

			start = tick / song.header.tempo
			asset_start = inpoint
			duration = outpoint - inpoint
			start, end = ensure_section_time(start, duration, min_time, max_time)
			times.append((start, asset_start, end))
		
		# Add clip to the video
		for start, asset_start, end in times:
			clip = hitfilm.Clip(track_id, asset, start, duration=end)
			clip.set_position(x, y)
			clip.set_size(w, h)
			clip.subclip(asset_start)
			
			project.add_clip(clip)
			
			# TWO OPTIONS HERE: 1) Either make Clip completely independent of the project,
			# and only generate a UUID on project.add_clip(), or require a new instance of
			# Clip everytime a new clip is added.

			print("Rendering {} '{}' at {:.1f} seconds".format(type, name, start))


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