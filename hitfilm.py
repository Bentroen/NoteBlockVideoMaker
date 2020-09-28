import uuid
import os
import cv2


class Clip():
	def __init__(self, track_id, asset, start, duration=None, asset_start=None, x=0, y=0, width=None, height=None, speed=1):
		self.id = uuid.uuid4()
		self.track_id = track_id
		self.asset = asset
		self.start = start
		self.duration = duration if duration else self.asset.duration
		self.asset_start = asset_start if asset_start else self.asset.inpoint
		self.anchorx = 0
		self.anchory = 0
		self.x = x
		self.y = y
		self.width = width
		if not width:
			self.width = self.asset.width
		self.height = height
		if not height:
			self.height = self.asset.height
		self.speed = speed
		
	def set_position(self, x, y):
		mw = self.asset.width
		mh = self.asset.height
		self.anchorx = -mw / 2
		self.anchory = mh / 2
		self.posx = x - (1920 // 2) # HARDCODED: get from project
		self.posy = (1080 // 2) - y #+ (1080 // 2)
		
	def set_size(self, width, height):
		self.width = width
		self.height = height
	
	def set_start(self):
		pass#self.asset_start
	
	def set_length(self):
		pass
		
	def get_scale(self):
		mw = self.asset.width
		mh = self.asset.height
		scalex = (self.width * 100) / mw
		scaley = (self.height * 100) / mh
		print(mw, mh, self.width, self.height, scalex, scaley)
		return scalex, scaley
		
	def get_time(self):
		fps = self.asset.fps
		startframe = int(round(self.start * fps))
		endframe = int(round((self.start + self.duration) * fps))
		return startframe, endframe
	
	def get_string(self):
		str = """
			<AssetVisualObject Version="0">
				<AssetType>0</AssetType>
				<AssetID>{}</AssetID>
				<AssetInstanceStart>{}</AssetInstanceStart>
				<IsTemplate>0</IsTemplate>
					<VisualObject Version="9">
						<BlendMode>0</BlendMode>
						<MotionBlur>0</MotionBlur>
						<Masks/>
						<BehaviorEffects/>
						<ObjectBase Version="2">
							<ID>{}</ID>
							<SequenceID>f77f563e-ec32-43d1-a006-72e464a24dbe</SequenceID>
							<ParentTrackID>{}</ParentTrackID>
							<LinkedObjectID>00000000-0000-0000-0000-000000000000</LinkedObjectID>
							<Name>{}</Name>
							<StartFrame>{}</StartFrame>
							<EndFrame>{}</EndFrame>
							<Label>-1</Label>
							<Effects/>
							<PropertyManager Version="7">
								<Prop Spatial="0" Type="0" CanInterpT="1">
									<Name>opacity</Name>
									<Default V="4">
										<fl>100</fl>
									</Default>
								</Prop>
								<Prop Spatial="1" Type="0" CanInterpT="1">
									<Name>position</Name>
									<Default V="4">
										<p2 X="{}" Y="{}"/>
									</Default>
								</Prop>
								<Prop Spatial="0" Type="0" CanInterpT="1">
									<Name>anchorPoint</Name>
									<Default V="4">
										<p2 X="{}" Y="{}"/>
									</Default>
								</Prop>
								<Prop Spatial="0" Type="0" CanInterpT="1">
									<Name>scale</Name>
									<Default V="4">
										<sc X="{}" Y="{}" Z="100"/>
									</Default>
								</Prop>
								<Prop Spatial="0" Type="1" CanInterpT="0">
									<Name>scaleLinked</Name>
									<Default V="4">
										<b>1</b>
									</Default>
								</Prop>
								<Prop Spatial="0" Type="0" CanInterpT="1">
									<Name>rotationZ</Name>
									<Default V="4">
										<fl>0</fl>
									</Default>
								</Prop>
								<Prop Spatial="0" Type="1" CanInterpT="1">
									<Name>speed</Name>
									<Default V="4">
										<db>{}</db>
									</Default>
								</Prop>
							</PropertyManager>
						</ObjectBase>
					</VisualObject>
				</AssetVisualObject>
			""".format(self.asset.id, self.asset_start, self.id, self.track_id, "Clip", *self.get_time(), self.posx, self.posy, self.anchorx, self.anchory, *self.get_scale(), self.speed)
		return str


class MediaAsset():
	def __init__(self, filename, name):
		self.filename = os.getcwd() + '\\' + filename.replace('/', '\\')
		self.name = name
		self.id = uuid.uuid4()
		self.instances = []
		self.inpoint = 0
		self.outpoint = None
		self.width, self.height, self.framecount, self.fps, self.duration = self.get_source_data(filename)
		if not self.outpoint:
			self.outpoint = self.framecount
		
	def add_instance(self, id, type):
		# type: 0=video, 1=audio
		self.instances.append((id, type))
	
	def get_source_data(self, filename):
		video = cv2.VideoCapture(filename)
		width = video.get(cv2.CAP_PROP_FRAME_WIDTH)
		height = video.get(cv2.CAP_PROP_FRAME_HEIGHT)
		framecount = video.get(cv2.CAP_PROP_FRAME_COUNT)
		fps = video.get(cv2.CAP_PROP_FPS)
		duration = framecount / fps
		return width, height, framecount, fps, duration
	
	def get_string(self):
		return 	"""
				<MediaAsset Version="9">
					<ID>{}</ID>
					<Name>{}</Name>
					<ParentFolderID>00000000-0000-0000-0000-000000000000</ParentFolderID>
					<IsHidden>0</IsHidden>
					<Filename>{}</Filename>
					<IsImageSequence>0</IsImageSequence>
					<HWAccelerate>1</HWAccelerate>
					<MergedAudioFilename/>
					<MergedAudioOffset>0</MergedAudioOffset>
					<VideoIdx>0</VideoIdx>
					<AudioIdx>0</AudioIdx>
					<OverrideFrameRate>0</OverrideFrameRate>
					<FrameRate>30</FrameRate>
					<OverridePAR>0</OverridePAR>
					<PAR>0</PAR>
					<OverrideAlpha>0</OverrideAlpha>
					<AlphaMode>0</AlphaMode>
					<OverrideColorLevels>0</OverrideColorLevels>
					<ColorLevels>0</ColorLevels>
					<OverrideColorSpace>0</OverrideColorSpace>
					<ColorSpace>0</ColorSpace>
					<InPoint>{}</InPoint>
					<OutPoint>{}</OutPoint>
					{}
				</MediaAsset>
				""".format(self.id, self.name, self.filename, self.inpoint, self.outpoint, \
							self.formatted_instances())

	def formatted_instances(self):
		if not self.instances:
			string = '<Instances/>'
		else:
			string = '<Instances>' + ''.join('<Instance ID="{}" Type="{}"/>'.format(id, type) for id, type in self.instances) + '</Instances>'
		return string


class Track():
	def __init__(self, name):
		self.name = name
		self.id = uuid.uuid4()
		self.objects = {} 
		
	def add_object(self, object):
		self.objects[object.id] = object
	
	def get_string(self):
		string = """
			<VideoTrack Version="2">
				<ID>{}</ID>
				<Name>{}</Name>
				<Visible>1</Visible>
				<Locked>0</Locked>
				{}
			</VideoTrack>
			""".format(self.id, self.name, self.formatted_objects())
		return string
	
	def formatted_objects(self):
		if not self.objects:
			string = '<Objects/>'
		else:
			string = '<Objects>' + ''.join(obj.get_string() for obj in self.objects.values()) + '</Objects>'
		return string
		

class Project():
	def __init__(self, duration=1000, width=1920, height=1080, framerate=30, samplerate=48000):
		self.tree = self.load_tree()
		self.media = {}
		self.video_tracks = {}
		self.id = uuid.uuid4()
	
	def load_tree(self):
		with open("base.hfp") as f:
			#return ET.parse(f)
			return f.read()
	
	def add_media(self, filename, name):
		asset = MediaAsset(filename, name)
		self.media[asset.id] = asset
		return asset
		
	def add_track(self, name=None, type='video'):
		if type == 'video':
			if not name:
				name = "Video {}".format(len(self.video_tracks))
			track = Track(name)
			self.video_tracks[track.id] = track
		elif type == 'audio':
			pass #TODO
		return track.id
	
	def add_clip(self, clip): #, track, asset_id):
		#print(self.video_tracks)
		self.video_tracks[clip.track_id].add_object(clip)
		self.media[clip.asset.id].add_instance(clip.id, type=0)
		print(clip.id)
		
		#clip = self.clips[asset_id]
		#clip.add_instance(instance_id, type)
		#self.video_tracks[track_id].add_object(clip)
	
	def save(self, filename):
		with open("base.hfp") as f:
			base = f.read()
		
		media_tree = []
		if not self.media:
			media_string = '<Assets/>'
		else:
			for id, asset in self.media.items():
				media_tree.append(asset.get_string())
			media_string = '<Assets>' + ''.join(media_tree) + '</Assets>'
		
		if not self.video_tracks:
			self.track_string = '<Tracks/>'
		else:
			track_tree = [track.get_string() for track in self.video_tracks.values()]
			track_string = ''.join(track_tree)
							
		with open(filename, 'w') as f:
			f.write(base.format(project_id = self.id,
								project_name = os.path.basename(filename),
								assets = media_string,
								video_tracks = track_string)
					)