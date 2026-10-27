from ollama_code.app import is_conversational, SYSTEM

def test_greetings():
    assert all(is_conversational(x) for x in ('Hi', 'Hello!', 'What are you?', 'How are you?'))

def test_coding_keeps_tools():
    assert not is_conversational('Fix my Python app')
    assert not is_conversational('Hi, can you inspect the repository and fix it?')

def test_identity():
    assert 'unofficial AI coding assistant' in SYSTEM
    assert 'respond naturally' in SYSTEM
