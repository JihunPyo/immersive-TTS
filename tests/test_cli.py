from immersive_tts.cli import main


def test_classify_reads_file(tmp_path, capsys):
    f = tmp_path / "sample.txt"
    f.write_text("안녕하세요.", encoding="utf-8")

    assert main(["classify", str(f)]) == 0
    assert "6자 읽음" in capsys.readouterr().out
