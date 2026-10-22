import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from tools.calculator import calculate
from tools.files import write_file, read_file, list_files, delete_file
from core.memory import memory_store
from core.rag import rag_pipeline
from core.safety import safety_manager

class TestJarvisSystem(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_01_health_endpoint(self):
        """Verify /health endpoint returns online status and JARVIS identity."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["assistant"], "JARVIS")
        self.assertEqual(data["user"], "Mahi")

    def test_02_calculator_tool(self):
        """Verify mathematical AST calculation tool."""
        res1 = calculate("25 * 40 + 100")
        self.assertTrue(res1["success"])
        self.assertEqual(res1["result"], 1100)

        res2 = calculate("sqrt(144) + 8")
        self.assertTrue(res2["success"])
        self.assertEqual(res2["result"], 20)

    def test_03_memory_store_and_extraction(self):
        """Verify memory extraction and persistence."""
        facts = memory_store.extract_facts("Remember that my favorite drink is iced coffee.")
        self.assertTrue(len(facts) > 0)
        saved = memory_store.save_memory("User's favorite drink is iced coffee")
        self.assertIn("fact", saved)

        search_res = memory_store.search_memory("What is my favorite drink?")
        self.assertTrue(len(search_res) > 0)
        self.assertIn("iced coffee", search_res[0]["fact"].lower())

    def test_04_rag_retrieval(self):
        """Verify RAG document ingestion and vector similarity search."""
        chunks = rag_pipeline.retrieve("protocols safety confirmation", top_k=2)
        self.assertTrue(len(chunks) > 0)
        # Should retrieve content from jarvis_manual.md mentioning Protocol Alpha
        found_text = " ".join([c["text"] for c in chunks])
        self.assertTrue("Protocol" in found_text or "Safety" in found_text or "JARVIS" in found_text)

    def test_05_chat_routing_calculator(self):
        """Verify chat endpoint routes math queries to calculator."""
        res = self.client.post("/chat", json={"message": "Calculate 50 * 50"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "calculator")
        self.assertIn("2500", data["reply"])

    def test_06_files_and_consequential_confirmation(self):
        """Verify files tool and consequential action confirmation workflow."""
        # 1. Create a test file
        w_res = write_file("test_sample.txt", "Automated test data.")
        self.assertTrue(w_res["success"])
        
        # 2. Read back
        r_res = read_file("test_sample.txt")
        self.assertTrue(r_res["success"])
        self.assertEqual(r_res["content"], "Automated test data.")

        # 3. Requesting delete via chat triggers consequential action confirmation
        chat_del = self.client.post("/chat", json={"message": "delete file test_sample.txt"})
        self.assertEqual(chat_del.status_code, 200)
        del_data = chat_del.json()
        self.assertIsNotNone(del_data["pending_action"])
        action_id = del_data["pending_action"]["action_id"]

        # 4. Confirm action
        confirm_res = self.client.post("/chat/confirm", json={"action_id": action_id, "approved": True})
        self.assertEqual(confirm_res.status_code, 200)
        self.assertEqual(confirm_res.json()["status"], "executed")

        # 5. Check file is now deleted
        r_del = read_file("test_sample.txt")
        self.assertFalse(r_del["success"])

    def test_07_vision_endpoint(self):
        """Verify /vision/analyze endpoint handles image uploads."""
        # Create a tiny 1x1 GIF / PNG byte payload
        tiny_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        files = {"file": ("test.png", tiny_png, "image/png")}
        data = {"prompt": "What is this image?"}
        res = self.client.post("/vision/analyze", files=files, data=data)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["success"])

    def test_08_device_control_open_app(self):
        """Verify intent routing and execution for opening desktop applications."""
        res = self.client.post("/chat", json={"message": "open chrome"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "action")
        self.assertIn("device_open_app", data["tools_used"])
        self.assertIn("Google Chrome", data["reply"])

    def test_09_device_control_youtube(self):
        """Verify intent routing for YouTube media command."""
        res = self.client.post("/chat", json={"message": "play lofi beats on youtube"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "action")
        self.assertIn("device_play_youtube", data["tools_used"])
        self.assertIn("lofi beats", data["reply"])

    def test_10_device_control_youtube_play_telugu_song(self):
        """Verify intent routing and execution for 'open youtube and play a telugu song'."""
        res = self.client.post("/chat", json={"message": "open youtube and play a telugu song"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "action")
        self.assertIn("device_play_youtube", data["tools_used"])
        self.assertIn("telugu song", data["reply"].lower())

    def test_11_device_control_animerulz_in_chrome(self):
        """Verify intent routing and execution for 'open naruto in animerulz in chrome'."""
        res = self.client.post("/chat", json={"message": "open naruto in animerulz in chrome"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "action")
        self.assertIn("device_open_site", data["tools_used"])
        self.assertIn("animerulz.in", data["open_url"])
        self.assertIn("naruto", data["open_url"].lower())

    def test_12_device_control_gerund_opening_naruto(self):
        """Verify user's exact command 'opening naruto on animerulz in chrome' routes and executes."""
        res = self.client.post("/chat", json={"message": "opening naruto on animerulz in chrome"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "action")
        self.assertIn("device_open_site", data["tools_used"])
        self.assertIn("animerulz.in/?s=naruto", data["open_url"].lower())
        self.assertIn("Opening Naruto on AnimeRulz", data["reply"])

    def test_13_device_control_animerulz_search_variations(self):
        """Verify variations like 'open animerulz and search naruto'."""
        res = self.client.post("/chat", json={"message": "open animerulz and search naruto"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "action")
        self.assertIn("animerulz.in/?s=naruto", data["open_url"].lower())

    def test_14_all_anime_platforms(self):
        """Verify queries across multiple anime platforms (Crunchyroll, HiAnime, 9Anime)."""
        # Crunchyroll
        res1 = self.client.post("/chat", json={"message": "watch one piece on crunchyroll"})
        self.assertEqual(res1.status_code, 200)
        self.assertIn("crunchyroll.com/search?q=one+piece", res1.json()["open_url"].lower())

        # HiAnime
        res2 = self.client.post("/chat", json={"message": "watch solo leveling on hianime"})
        self.assertEqual(res2.status_code, 200)
        self.assertIn("hianime.to/search?keyword=solo+leveling", res2.json()["open_url"].lower())

    def test_15_watch_anime_auto_route(self):
        """Verify that saying 'watch demon slayer' auto-routes to anime search."""
        res = self.client.post("/chat", json={"message": "watch demon slayer"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "action")
        self.assertIn("animerulz.in/?s=demon+slayer", data["open_url"].lower())

    def test_16_open_documents_folder(self):
        """Verify 'open documents' opens laptop Documents folder, NOT Chrome."""
        res = self.client.post("/chat", json={"message": "open documents"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "action")
        self.assertIn("device_open_app", data["tools_used"])
        self.assertIsNone(data["open_url"])
        self.assertIn("Documents", data["reply"])

    def test_17_open_camera_and_hardware(self):
        """Verify 'open camera' opens native camera on laptop without browser."""
        res = self.client.post("/chat", json={"message": "open camera"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "action")
        self.assertIn("device_open_app", data["tools_used"])
        self.assertIsNone(data["open_url"])
        self.assertIn("Camera", data["reply"])

    def test_18_open_my_documents_variant(self):
        """Verify natural phrasing 'open my documents'."""
        res = self.client.post("/chat", json={"message": "open my documents"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "action")
        self.assertIn("device_open_app", data["tools_used"])
        self.assertIsNone(data["open_url"])
        self.assertIn("Documents", data["reply"])

    def test_19_list_documents_folder(self):
        """Verify 'list documents' lists folder files."""
        res = self.client.post("/chat", json={"message": "list documents"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "action")
        self.assertIn("device_list_folder", data["tools_used"])
        self.assertIsNone(data["open_url"])
        self.assertIn("Documents folder", data["reply"])

    def test_20_open_jarvi_interface_image_on_desktop(self):
        """Verify 'open jarvi interface jpj in desktop' matches and opens jarvi interface.jpeg."""
        res = self.client.post("/chat", json={"message": "open jarvi interface jpj in desktop"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "action")
        self.assertIn("device_find_and_open_file", data["tools_used"])
        self.assertIn("jarvi interface.jpeg", data["reply"])

    def test_21_open_interface_compulsory_ui(self):
        """Verify 'open interface' and 'show dashboard' explicitly trigger compulsory UI mode."""
        from core.agent import jarvis_agent, should_open_interface
        res = self.client.post("/chat", json={"message": "open interface"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("open_jarvis_interface", data["tools_used"])
        self.assertEqual(data["action_type"], "open_ui")
        self.assertTrue(should_open_interface(data))

    def test_22_headless_classification(self):
        """Verify standard OS tools, folders, apps, and calculations remain headless (UI closed)."""
        from core.agent import jarvis_agent, should_open_interface
        for query in ["open chrome", "open documents", "calculate 50 * 20", "open notepad"]:
            r = jarvis_agent.process_request(query)
            self.assertFalse(should_open_interface(r), f"Failed for query: {query}")

    def test_23_speech_text_sanitizer(self):
        """Verify markdown, links, bullet points, and code markers are cleaned for TTS."""
        from services.tts_service import clean_text_for_speech
        raw = "Opening **Documents** folder on your laptop, Mahi. • `1711.pdf` [view](http://example.com)"
        cleaned = clean_text_for_speech(raw)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("`", cleaned)
        self.assertNotIn("http://", cleaned)
        self.assertIn("Opening Documents folder", cleaned)

    def test_24_wake_word_command_extraction(self):
        """Verify wake words ('hello jarvis', 'jarvis') are detected and stripped cleanly."""
        from services.background_voice_daemon import extract_command_from_utterance
        self.assertEqual(extract_command_from_utterance("hello jarvis open chrome"), "open chrome")
        self.assertEqual(extract_command_from_utterance("hey jarvis open documents"), "open documents")
        self.assertEqual(extract_command_from_utterance("jarvis play lofi beats"), "play lofi beats")
        self.assertEqual(extract_command_from_utterance("hello jarvis"), "")
        self.assertIsNone(extract_command_from_utterance("good morning everyone"))

    def test_25_normal_information_question_routing(self):
        """Verify general information question routes to AI service and returns an answer."""
        from services.ai_service import ai_service
        with patch.object(ai_service, "is_configured", return_value=True), \
             patch.object(ai_service, "ask_ai", return_value="Python is a high-level, general-purpose programming language.") as mock_ask:
            res = self.client.post("/chat", json={"message": "what is python"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["intent"], "chat")
            self.assertIn("ai_service", data["tools_used"])
            self.assertIn("Python is a high-level", data["reply"])
            mock_ask.assert_called_once()

    def test_26_action_command_never_sent_to_ai_model(self):
        """Verify action command ('open chrome') routes to existing tool and never calls AI service."""
        from services.ai_service import ai_service
        with patch.object(ai_service, "ask_ai") as mock_ask:
            res = self.client.post("/chat", json={"message": "open chrome"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["intent"], "action")
            self.assertIn("device_open_app", data["tools_used"])
            self.assertNotIn("ai_service", data.get("tools_used", []))
            mock_ask.assert_not_called()

    def test_27_ai_api_failure_graceful_fallback(self):
        """Verify OpenAI API failure falls back to polite JARVIS offline notification."""
        from services.ai_service import ai_service, OFFLINE_FALLBACK_MESSAGE
        with patch.object(ai_service, "is_configured", return_value=True), \
             patch.object(ai_service, "_get_client") as mock_client:
            client_mock = MagicMock()
            client_mock.responses.create.side_effect = Exception("OpenAI API unreachable")
            client_mock.chat.completions.create.side_effect = Exception("OpenAI API unreachable")
            mock_client.return_value = client_mock
            
            res = self.client.post("/chat", json={"message": "explain machine learning"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["reply"], OFFLINE_FALLBACK_MESSAGE)
            self.assertEqual(data["reply"], "Sir, my online intelligence service is currently unavailable. I can still perform my local JARVIS commands.")

    def test_28_missing_api_key_returns_unconfigured_message(self):
        """Verify missing/unconfigured API key returns exact notification."""
        from services.ai_service import ai_service, NOT_CONFIGURED_MESSAGE
        with patch.object(ai_service, "is_configured", return_value=False):
            res = self.client.post("/chat", json={"message": "what is recursion"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["reply"], NOT_CONFIGURED_MESSAGE)
            self.assertEqual(data["reply"], "Online AI intelligence is not configured yet.")

    def test_29_tts_compatible_response_cleaning(self):
        """Verify TTS text sanitizer strips markdown, URLs, bullet points, and code markers."""
        from services.ai_service import ai_service
        raw_ai_text = "### **Neural Networks**\n`Deep learning` models use [backprop](https://en.wikipedia.org/wiki/Backpropagation) • *Weights* & ~biases~."
        speech_text = ai_service.get_speech_friendly_text(raw_ai_text)
        self.assertNotIn("###", speech_text)
        self.assertNotIn("**", speech_text)
        self.assertNotIn("`", speech_text)
        self.assertNotIn("https://", speech_text)
        self.assertNotIn("•", speech_text)
        self.assertNotIn("*", speech_text)
        self.assertNotIn("~", speech_text)
        self.assertIn("Neural Networks", speech_text)
        self.assertIn("Deep learning models use backprop", speech_text)

    def test_30_rag_question_routing_prefers_local_docs(self):
        """Verify questions matching local documents prefer local RAG pipeline over external AI."""
        res = self.client.post("/chat", json={"message": "protocols safety confirmation"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "document")
        self.assertIn("rag_retrieval", data["tools_used"])
        self.assertTrue("Protocol" in data["reply"] or "JARVIS" in data["reply"] or "Safety" in data["reply"])

    def test_31_current_information_question_routing(self):
        """Verify current-information question triggers web search tool and AI synthesis."""
        from services.ai_service import ai_service
        with patch.object(ai_service, "is_configured", return_value=True), \
             patch.object(ai_service, "ask_ai", return_value="NVIDIA's latest consumer GPUs include the RTX 50 series based on the Blackwell architecture.") as mock_ask:
            res = self.client.post("/chat", json={"message": "latest nvidia gpu"})
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["intent"], "search")
            self.assertIn("web_search", data["tools_used"])
            self.assertIn("ai_service", data["tools_used"])
            mock_ask.assert_called_once()
            self.assertIn("RTX 50 series", data["reply"])

    def test_32_safety_system_unaffected_protocol_alpha(self):
        """Verify safety system remains strictly active; AI cannot bypass confirmation for consequential actions."""
        res = self.client.post("/chat", json={"message": "delete file dangerous_system_file.txt"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["intent"], "action")
        self.assertIsNotNone(data["pending_action"])
        self.assertIn("Consequential action detected", data["reply"])
        self.assertNotIn("ai_service", data.get("tools_used", []))

if __name__ == "__main__":
    unittest.main()



