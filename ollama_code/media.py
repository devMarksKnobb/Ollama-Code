"""Explicit, bounded attachments for Ollama Code conversations."""
import base64
import shutil
import subprocess
import tempfile
from pathlib import Path

IMAGE_EXT={'.png','.jpg','.jpeg','.webp'}
TEXT_EXT={'.py','.js','.ts','.tsx','.jsx','.md','.txt','.json','.yaml','.yml','.toml','.html','.css','.rs','.go','.java','.sh','.c','.cpp','.h','.hpp','.xml','.sql','.rb','.php'}
VIDEO_EXT={'.mp4','.mov','.mkv','.webm'}
MAX_IMAGE=12*1024*1024
MAX_TEXT=128*1024
MAX_VIDEO=250*1024*1024

def resolve_attachment(raw, workspace):
    path=Path(raw).expanduser()
    if not path.is_absolute():path=Path(workspace)/path
    path=path.resolve(strict=True)
    if not path.is_file():raise ValueError('Attachment must be a regular file')
    return path

def attach_text(raw,workspace):
    path=resolve_attachment(raw,workspace)
    if path.suffix.lower() not in TEXT_EXT:raise ValueError('Unsupported text extension')
    if path.stat().st_size>MAX_TEXT:raise ValueError('Text attachment exceeds 128 KiB; use /code or project search for larger files')
    content=path.read_text(encoding='utf-8')
    return {'kind':'text','path':str(path),'content':content}

def attach_image(raw,workspace):
    path=resolve_attachment(raw,workspace)
    if path.suffix.lower() not in IMAGE_EXT:raise ValueError('Supported images: PNG, JPEG, WebP')
    if path.stat().st_size>MAX_IMAGE:raise ValueError('Image exceeds 12 MiB')
    return {'kind':'image','path':str(path),'data':base64.b64encode(path.read_bytes()).decode('ascii')}

def attach_video(raw,workspace):
    path=resolve_attachment(raw,workspace)
    if path.suffix.lower() not in VIDEO_EXT:raise ValueError('Supported videos: MP4, MOV, MKV, WebM')
    if path.stat().st_size>MAX_VIDEO:raise ValueError('Video exceeds 250 MiB')
    if not shutil.which('ffmpeg'):raise RuntimeError('Video frame extraction requires ffmpeg installed on your system')
    with tempfile.TemporaryDirectory(prefix='ollama-code-frames-') as tmp:
        pattern=str(Path(tmp)/'frame-%02d.jpg')
        proc=subprocess.run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-i',str(path),'-vf','fps=1/15,scale=640:-2','-frames:v','4','-y',pattern],capture_output=True,text=True,timeout=90)
        if proc.returncode:raise RuntimeError('ffmpeg could not decode video: '+proc.stderr[:350])
        frames=sorted(Path(tmp).glob('frame-*.jpg'))
        if not frames:raise RuntimeError('No video frames could be extracted')
        images=[base64.b64encode(f.read_bytes()).decode('ascii') for f in frames]
    return {'kind':'video','path':str(path),'frames':images}

class Attachments:
    def __init__(self,workspace):self.workspace=workspace;self.items=[]
    def add(self,kind,path):
        item={'read':attach_text,'image':attach_image,'video':attach_video}[kind](path,self.workspace)
        self.items.append(item)
        return f"Attached {kind}: {item['path']}" + (f" ({len(item['frames'])} sampled frames)" if kind=='video' else '')
    def pop_message(self,prompt):
        items=self.items[:]
        self.items.clear()
        chunks=[prompt];images=[]
        for item in items:
            if item['kind']=='text':chunks.append(f"\n\nAttached file {item['path']}:\n```\n{item['content']}\n```")
            elif item['kind']=='image':images.append(item['data']);chunks.append(f"\nAttached image: {item['path']}")
            else:images.extend(item['frames']);chunks.append(f"\nAttached video sampled as {len(item['frames'])} still frames: {item['path']}. Motion and audio are not provided.")
        message={'role':'user','content':'\n'.join(chunks)}
        if images:message['images']=images
        return message
