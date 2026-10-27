from ollama_code.media import Attachments, attach_text, attach_image, attach_video
import pytest

def test_text_attachment(tmp_path):
    (tmp_path/'hello.py').write_text('print(42)')
    a=Attachments(tmp_path)
    assert 'Attached' in a.add('read','hello.py')
    message=a.pop_message('explain')
    assert 'print(42)' in message['content']
    assert not a.items

def test_image_attachment(tmp_path):
    (tmp_path/'pic.png').write_bytes(b'abc')
    a=Attachments(tmp_path);a.add('image','pic.png')
    assert a.pop_message('describe')['images']==['YWJj']

def test_missing_video_tool(tmp_path,monkeypatch):
    (tmp_path/'clip.mp4').write_bytes(b'abc')
    monkeypatch.setattr('ollama_code.media.shutil.which',lambda x:None)
    with pytest.raises(RuntimeError,match='ffmpeg'):attach_video('clip.mp4',tmp_path)

def test_reject_large_text(tmp_path):
    (tmp_path/'huge.txt').write_bytes(b'x'*131073)
    with pytest.raises(ValueError,match='128 KiB'):attach_text('huge.txt',tmp_path)
