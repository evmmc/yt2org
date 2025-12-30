import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add parent directory to path to import yt2org
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yt2org

class TestYt2Org(unittest.TestCase):
    def test_extract_live_video_id(self):
        url = "https://www.youtube.com/live/KijwP7D-BBo"
        expected_id = "KijwP7D-BBo"
        self.assertEqual(yt2org.extract_live_video_id(url), expected_id)

    def test_extract_standard_video_id_short(self):
        # This corresponds to one of the URLs provided by the user, although strictly speaking 
        # youtube.com/KijwP7D-BBo is not a standard format, it usually redirects or is a short link 
        # but often lacks the 'v='. However, the regex seems designed to catch ID at the end.
        # Let's see if the regex handles `youtube.com/ID` which is what the user provided: `https://www.youtube.com/KijwP7D-BBo`
        # Actually `https://www.youtube.com/KijwP7D-BBo` usually isn't a valid video link, it's `youtu.be/KijwP7D-BBo` or `youtube.com/watch?v=...`
        # But the user provided it, so let's see if the tool supports it.
        # The regex `pattern = r'(?:https?://)?(?:www eitet)?(?:youtube\.com/(?:[^/\n\s]+/[^/]+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be/)([a-zA-Z0-9_-]{11})'`
        # looks like it expects `v/` or `embed/` or `watch?v=`.
        # `youtu.be/` is also supported.
        # `https://www.youtube.com/KijwP7D-BBo` might fail with the current regex even if fixed. 
        # But let's test what the user gave.
        
        url = "https://www.youtube.com/KijwP7D-BBo"
        # If the user meant this to be a valid input, the code should handle it. 
        # However, looking at the regex: `youtu\.be/` works. `youtube.com/...` expects specific paths.
        # Let's assuming the user meant `youtu.be` OR the code intends to support `youtube.com/ID`.
        # If I look at the live regex: `...|live)\/|\S*?[?&]v=)|youtu\.be/)...`
        
        # Let's test the standard watch URL too.
        url_watch = "https://www.youtube.com/watch?v=KijwP7D-BBo"
        expected_id = "KijwP7D-BBo"
        self.assertEqual(yt2org.extract_standard_video_id(url_watch), expected_id)

    def test_extract_standard_video_id_user_provided(self):
         # The user explicitly provided `https://www.youtube.com/KijwP7D-BBo`
         url = "https://www.youtube.com/KijwP7D-BBo"
         expected_id = "KijwP7D-BBo"
         self.assertEqual(yt2org.extract_standard_video_id(url), expected_id) 

    @patch('yt2org.YoutubeDL')
    def test_get_video_title(self, mock_ydl):
        mock_instance = mock_ydl.return_value
        mock_instance.__enter__.return_value.extract_info.return_value = {'title': 'Test Video Title'}
        
        url = "https://www.youtube.com/watch?v=KijwP7D-BBo"
        title = yt2org.get_video_title(url)
        self.assertEqual(title, "Test-Video-Title")

if __name__ == '__main__':
    unittest.main()
