import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from files import read_text_file, search_files
from mail import mail
from speech import Speech


class BruceTests(unittest.TestCase):
    def test_text_is_not_executed_and_truncation_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "message.txt"
            path.write_text('$(touch unwanted)\nHello "Dad" — café', encoding="utf-8")
            result = read_text_file(str(path), 10)
            self.assertTrue(result["truncated"])
            self.assertEqual(result["text"], "$(touch un")
            self.assertFalse((Path(directory) / "unwanted").exists())

    def test_mail_payload_is_json_not_source(self):
        import json

        text = '"; throw Error("injection"); //\nHello Dad'

        def fake_run(args, **kwargs):
            payload = json.loads(Path(args[-1]).read_text())
            self.assertEqual(payload["text"], text)
            self.assertNotIn(text, args)
            return '{"sent": false}'

        with patch("common.run_command", side_effect=fake_run):
            self.assertFalse(mail("draft", id=123, text=text)["sent"])

    def test_speech_rejects_empty_and_invalid_rate_before_launch(self):
        speech = Speech()
        with patch("speech.subprocess.Popen") as popen:
            with self.assertRaises(ValueError):
                speech.start("")
            with self.assertRaises(ValueError):
                speech.start("Hello", rate=0)
            popen.assert_not_called()

    def test_message_blob_text_and_handle_matching(self):
        from texts import handle_key, message_text

        short = b"streamtyped\x84NSAttributedString\x00\x84NSString\x01\x94\x84\x01+\x07Hi \xf0\x9f\x91\x8b\x86"
        self.assertEqual(message_text(None, short), "Hi \U0001f44b")
        long_text = "x" * 300
        blob = (
            b"NSString\x01\x94\x84\x01+\x81"
            + (300).to_bytes(2, "little")
            + long_text.encode()
        )
        self.assertEqual(message_text(None, blob), long_text)
        self.assertEqual(message_text("plain", blob), "plain")
        self.assertEqual(handle_key("+1 (555) 123-4567"), handle_key("5551234567"))
        self.assertEqual(handle_key("Dad@Example.com "), "dad@example.com")

    def test_send_text_requires_confirmation_before_any_action(self):
        from texts import send_text

        with patch("texts.run_command") as run, patch("texts.query") as query:
            with self.assertRaises(ValueError):
                send_text(1, "Hello", confirmed=False)
            run.assert_not_called()
            query.assert_not_called()

    def test_file_search_rejects_option_like_text_and_filters_library(self):
        with self.assertRaises(ValueError):
            search_files("-onlyin /")
        with tempfile.TemporaryDirectory() as directory:
            doc = Path(directory) / "Letter.txt"
            doc.write_text("hi")
            hidden = Path(directory) / "Library" / "cache.txt"
            with patch(
                "files.run_command", return_value=f"{hidden}\n{doc}\n/missing/file"
            ):
                result = search_files("letter")
        self.assertEqual([f["name"] for f in result["files"]], ["Letter.txt"])

    def test_browser_rejects_non_web_addresses_and_unknown_browsers(self):
        from browser import open_url

        with patch("browser.run_command") as run:
            for url in ("file:///etc/passwd", "javascript:alert(1)"):
                with self.assertRaises(ValueError):
                    open_url(url)
            with self.assertRaises(ValueError):
                open_url("https://www.hulu.com", "firefox")
            run.assert_not_called()

    def test_local_brain_sends_only_after_bruces_yes(self):
        import brain

        answers = []
        with patch("brain.ensure_server"):  # No model server in unit tests.
            brain = brain.Brain(confirm=lambda question: answers.pop(0))
        args = {"chat_id": 7, "text": "Running late", "user_confirmed": True}
        with (
            patch("brain.chat_title", return_value="Mom"),
            patch("texts.send_text", return_value={"status": "sent"}) as send,
            patch("server.send_text", send),
        ):
            answers.append(False)
            self.assertEqual(
                brain.run_tool("send_text_message", args)["status"], "cancelled"
            )
            send.assert_not_called()
            answers.append(True)
            brain.run_tool("send_text_message", args)
            send.assert_called_once_with(7, "Running late", True)
        self.assertEqual(
            brain.run_tool("speak_text", {"text": "hi"})["status"], "error"
        )
        for label in ("Kids", " drew "):
            self.assertEqual(
                brain.run_tool("click_web_page", {"label": label})["status"], "error"
            )  # Refused by browser.click_page before any click.

    def test_replies_spell_out_abbreviations_for_listening(self):
        from brain import plain
        self.assertEqual(plain("**Sunny**, high 66°F, east wind 1 to 6 mph, 20% rain."),
                         "Sunny, high 66 degrees, east wind 1 to 6 miles per hour, "
                         "20 percent rain.")
        self.assertEqual(plain("About 3 mi away, approx. 10 min & 2 hrs"),
                         "About 3 miles away, about 10 minutes and 2 hours")
        self.assertEqual(plain("Minnesota in Helena"), "Minnesota in Helena")
        self.assertEqual(plain("1. From: Jim <jim@a.b.org> 2. Rated 4.5 stars"),
                         "From: Jim Rated 4.5 stars")
        self.assertEqual(plain("1. Hope 2. Jobs 3. $PATH versus $SNOW 4. Early access"),
                         "Hope Jobs $PATH versus $SNOW Early access")
        self.assertEqual(plain("A low around 41. The wind is calm."),
                         "A low around 41. The wind is calm.")
        self.assertEqual(plain("From: MyGreenhouse Email: no-reply@x.com Would you"),
                         "From: MyGreenhouse Would you")

    def test_mail_sender_name_and_local_time(self):
        from mail import friendly
        m = friendly({"sender": "James Talarico <james@substack.com>",
                      "received": "2026-10-20T22:20:00.000Z"})
        self.assertEqual((m["sender"], m["sender_email"]), ("James Talarico", "james@substack.com"))
        self.assertRegex(m["received"], r"at \d{1,2}:\d{2} [AP]M$")

    def test_stop_while_talking_ignores_brains_own_words(self):
        from brain_voice import interrupted
        spoken = "Tomorrow will be sunny with a high near 66 degrees."
        self.assertTrue(interrupted("sunny with a stop", spoken))
        self.assertTrue(interrupted("Okay, that's enough.", spoken))
        self.assertFalse(interrupted("sunny with a high near", spoken))
        self.assertFalse(interrupted("the bus stop is closed", "The bus stop is closed today."))

    def test_hotkey_flag_file_switches_mic_and_silences_brain(self):
        import tempfile
        import threading
        import time
        import brain_voice
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(brain_voice, "MIC_OFF_FLAG", Path(folder) / "mic_off"), \
             patch.object(brain_voice.speech, "stop") as stop:
            self.assertTrue(brain_voice.mic_on.is_set())
            threading.Thread(target=brain_voice.watch_switch, args=(0.02,), daemon=True).start()
            (Path(folder) / "mic_off").touch()  # What the hotkey script does.
            time.sleep(0.2)
            self.assertFalse(brain_voice.mic_on.is_set())
            self.assertTrue(brain_voice.CANCEL.is_set())
            stop.assert_called()
            brain_voice.mic_on.set()
            self.assertTrue(brain_voice.mic_on.is_set())
        brain_voice.CANCEL.clear()

    def test_saying_stop_cancels_a_running_task(self):
        import time
        import brain_voice
        from common import CANCEL, checkpoint

        class SlowBrain:
            def ask(self, request):
                for _ in range(100):  # A long task that checks for stop between steps.
                    time.sleep(0.05)
                    try:
                        checkpoint()
                    except Exception:
                        return None
                return "finished"

        heard = iter(["", "the weather", "stop"])
        start = time.time()
        answer = brain_voice.ask_while_listening(SlowBrain(), "play a show",
                                                 lambda: next(heard, ""))
        self.assertIsNone(answer)
        self.assertLess(time.time() - start, 3)
        CANCEL.clear()
        self.assertEqual(brain_voice.ask_while_listening(
            type("Quick", (), {"ask": lambda self, r: "done"})(), "hi", lambda: ""), "done")

    def test_whisper_loops_are_discarded(self):
        from brain_voice import hallucinated
        self.assertTrue(hallucinated("I have a really good one, " * 12))
        self.assertTrue(hallucinated("Thank you. Thank you so much. Thank you. Thank you so much. "
                                     "Thank you. Thank you so much."))
        self.assertFalse(hallucinated("Can you go to Prime Video and play Elsbeth, the latest "
                                      "episode, and then tell me the weather for tomorrow?"))
        self.assertFalse(hallucinated("Brain stop."))

    def test_voice_enrollment_commands_and_open_default(self):
        import numpy as np
        import brain_voice
        self.assertEqual(brain_voice.route("Brain, learn my voice.", True), ("learn", ""))
        self.assertEqual(brain_voice.route("Hey Brain, remember my voice", False), ("learn", ""))
        # With no voiceprint saved, every voice is accepted.
        with patch.object(brain_voice, "VOICEPRINT", Path("/nonexistent/voiceprint.npy")):
            self.assertTrue(brain_voice.is_bruce(np.zeros(16000, np.float32), 3.0))
        # Too short to judge ("yes", "stop") passes without loading the voice model.
        self.assertTrue(brain_voice.is_bruce(np.zeros(8000, np.float32), 0.5))

    def test_repeated_action_call_runs_once(self):
        import brain
        call = {"id": "1", "function": {"name": "play_tv_show",
                                        "arguments": '{"service": "hulu", "show": "High Potential"}'}}
        replies = iter([{"role": "assistant", "content": "", "tool_calls": [call]},
                        {"role": "assistant", "content": "", "tool_calls": [call]},
                        {"role": "assistant", "content": "It's playing."}])
        with patch("brain.ensure_server"):
            b = brain.Brain(confirm=lambda q: True)
        with patch("brain.chat", side_effect=lambda *a: next(replies)), \
             patch.object(b, "run_tool", return_value={"status": "playing"}) as run:
            self.assertEqual(b.ask("play High Potential on Hulu"), "It's playing.")
        run.assert_called_once()

    def test_mic_reads_stop_the_moment_hotkey_turns_it_off(self):
        import brain_voice

        class Stream:
            def read(self, size):
                return b"\0" * size

        source = type("Source", (), {"stream": Stream()})()
        brain_voice.stop_reads_when_off(source)
        self.assertEqual(len(source.stream.read(4)), 4)
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(brain_voice, "MIC_OFF_FLAG", Path(folder) / "mic_off"):
            brain_voice.mic_on.clear()
            with self.assertRaises(brain_voice.MicOff):
                source.stream.read(4)

    def test_brain_start_stop_and_background_talk(self):
        from brain_voice import route

        self.assertEqual(
            route("Hey Brain, read my email.", False), ("ask", "read my email.")
        )
        self.assertEqual(
            route("what about the second one", True),
            ("ask", "what about the second one"),
        )
        self.assertEqual(route("The weather tonight is cold", False), (None, ""))
        self.assertEqual(route("Thank you.", True), (None, ""))
        self.assertEqual(route("Brain stop.", True), ("sleep", ""))
        self.assertEqual(route("Brian, start", False), ("start", ""))
        self.assertEqual(route("Brain.", False), ("start", ""))
        self.assertEqual(route("Brain, shut down", True), ("quit", ""))
        self.assertEqual(
            route("Brain, stop the video", True), ("ask", "stop the video")
        )

    def test_play_button_never_buys_or_rents(self):
        from browser import SERVICES, play_button
        prime = SERVICES["prime video"]["buttons"]
        self.assertEqual(play_button(["Buy Season 1 $19.99", "Rent", "Play S1 E1"], prime),
                         "Play S1 E1")
        self.assertIsNone(play_button(["Watch with a free trial", "Buy Episode"], prime))
        self.assertEqual(play_button(["Watch Party", "WATCH NEXT EPISODE: S1 E2"],
                                     SERVICES["hulu"]["buttons"]), "WATCH NEXT EPISODE: S1 E2")
        self.assertEqual(play_button(["Play", "Resume"], SERVICES["netflix"]["buttons"]),
                         "Resume")
        with self.assertRaises(ValueError):
            from browser import play_show
            play_show("youtube tv", "News")

    def test_show_titles_match_despite_mishearing(self):
        from browser import matching_titles
        controls = ["Home", 'Search instead for "Elspeth".', "Elsbeth", "Elsbeth Resume S3 E18",
                    "Ellipsis", "Search for Elspeth"]
        self.assertIn("Elsbeth", matching_titles("Elspeth", controls))
        self.assertNotIn("Ellipsis", matching_titles("Elspeth", controls))
        self.assertEqual(matching_titles("High Potential", ["High Potential", "Home"]),
                         ["High Potential"])
        self.assertEqual(matching_titles("Reacher", ["Home", "Movies"]), [])

    def test_stop_does_not_signal_an_exited_process(self):
        from unittest.mock import Mock

        speech = Speech()
        speech.process = Mock()
        speech.process.poll.return_value = 0
        speech.stop()
        speech.process.terminate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
