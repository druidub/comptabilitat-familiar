"""Configuració global de pytest: mock de Streamlit per a tests sense UI."""
import sys
from unittest.mock import MagicMock

if "streamlit" not in sys.modules:
    _mock_st = MagicMock()
    _mock_st.cache_data = lambda **kw: (lambda f: f)
    sys.modules["streamlit"] = _mock_st
