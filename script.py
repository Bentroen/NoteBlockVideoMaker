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

def enforce_section_time(start, asset_start, duration, min_time, max_time):
	if start < min_time:
		start = min_time
		asset_start += (min_time - start)
		duration -= (min_time - start)

	if start + duration >= max_time:
		end = max_time - start
	else:
		end = duration
		
	return start, asset_start, end

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
	file = os.path.join("clips", path)
	asset, track_id = setup_clip(file, name)
	
	clip_parts = clip.get("parts")
	if clip_parts:
		print("a")
		parts = []
		for part in clip_parts:
			instrument = part["instrument"]
			start = part.get("start", 0)
			attack = part.get("attack", 0)
			end = part.get("end", asset.duration)
			all = [instrument, start, attack, end]
			parts.append(all)
		parts = list(zip(*parts))
	else:
		instrument = clip["instrument"]
		start = clip.get("start", 0)
		attack = clip.get("attack", 0)
		end = clip.get("end", asset.duration)
		parts = [[instrument], [start], [attack], [end]]
		
	clips[name] = (parts, asset, track_id)
	

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
		end = section.get("end", asset.duration)
		segments.append((start, end))
	tracks[name] = [instrument, 0, asset, track_id, segments]


# Place clips into final video for each section
video = []
last_tick = 0

for section_num, section in enumerate(config["sections"]):
	
	section_start = section["start"]
	section_end = section["end"]
	last_tick = section_end
	grid_size = section["grid_size"]
	
	print("\n==========================================")
	print("Starting render of section {} at tick {}".format(section_num + 1, section_start))
	print("==========================================\n")
	
	if section_start > song.header.song_length - 1:
		break
	
	cellw = WIDTH / grid_size
	cellh = HEIGHT / grid_size
	
	for item in section["clips"]:
		
		# Figure out if a clip or a track
		name = item["name"]
		if name in clips:
			type = "clip"
			parts, asset, track_id = clips[name]
			clip_times = {}
			for ins, inpoint, attack, outpoint in zip(*parts):
				clip_times[ins] = (inpoint, attack, outpoint)
			instruments = clip_times.keys()
		elif name in tracks:
			type = "track"
			ins, current_segment, asset, track_id, segments = tracks[name]
			instruments = [ins]
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
		dirty_notes = sorted(filter(lambda y: y.instrument in instruments, chunk), key=lambda z: z.tick)
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
				ins = note.instrument
				inpoint, attack, outpoint = clip_times[ins]
				
				# set clip to start exactly at the attack point
				start = tick / song.header.tempo
				asset_start = attack
				duration = outpoint - attack
				
				time_from_last_attack = start - last_attack
				attack_time = attack - inpoint

				# Use 1/4 of the last clip's "release" for the start of
				# the current clip, the time from the start to the attack
				# of the clip, or 1/4 of a second (whatever is smaller).
				advance = min(max(time_from_last_attack / 4, 0), attack_time, 0.25)
				
				choices = [max(time_from_last_attack / 4, 0), attack_time, 0.25]
				
				# move clip forward by the calculated start position
				asset_start -= advance
				start -= advance
				duration += advance
				
				# prevent clip from exceeding section time
				start, asset_start, end = enforce_section_time(start, asset_start, duration, min_time, max_time)
				
				times.append((start, asset_start, end))
				last_attack = start + attack_time
				
			print("Rendered clip {} {} times".format(name, len(notes) + 1))
				
		elif type == "track":
		
			current_trigger = 0
			previous_tick = notes[0].tick - 1
			for note in notes:
				tick = note.tick
				if current_trigger == 0 or (tick - previous_tick) >= TRIGGER_INTERVAL:
					
					inpoint, outpoint = segments[current_segment]
				
					start = tick / song.header.tempo
					print("Rendering segment {} of track {} at tick {}".format(current_segment + 1, name, tick))
					asset_start = inpoint
					duration = outpoint - inpoint
					start, asset_start, end = enforce_section_time(start, asset_start, duration, min_time, max_time)
					times.append((start, asset_start, end))
					
					# increase next segment to be used, and loop
					# back to first segment when running out
					current_segment += 1					
					current_segment += 1
					if current_segment > len(segments) - 1:
						current_segment = 0
					tracks[name][1] = current_segment
					
					# stop if number of triggers for this segment is reached
					if current_segment == triggers - 1:
					if current_trigger == triggers - 1:
						break
					
					current_trigger += 1
					
				previous_tick = tick
		
			try:
				note = notes[0]
			except IndexError as e:
				raise ValueError("Couldn't add track '{}' on section at tick {}: No note blocks with instrument {} were found".format(name, section_start, ins)) from None
			
			tick = note.tick
		
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


project.save("output.hfp")
