# Testing Plan: Telegram Food Tracker Bot

## Daftar Isi
1. [Overview](#1-overview)
2. [Testing Strategy](#2-testing-strategy)
3. [Unit Testing Plan](#3-unit-testing-plan)
4. [Integration Testing Plan](#4-integration-testing-plan)
5. [End-to-End Testing Plan](#5-end-to-end-testing-plan)
6. [Test Dependencies & Setup](#6-test-dependencies--setup)
7. [Test File Structure](#7-test-file-structure)
8. [Contoh Implementasi Test](#8-contoh-implementasi-test)
9. [CI/CD Integration](#9-cicd-integration)
10. [Prioritas & Timeline](#10-prioritas--timeline)

---

## 1. Overview

### 1.1 Cakupan Testing

Bot ini memiliki 3 modul utama yang perlu ditest:

| Modul | File | Fungsi Utama |
|-------|------|--------------|
| Configuration | `config.py` | Load environment variables |
| Gemini Service | `gemini_service.py` | Analisis makanan via AI |
| Bot Handler | `bot.py` | Handle pesan & command Telegram |

### 1.2 External Dependencies yang Perlu di-Mock

1. **Telegram Bot API** - Untuk menerima dan mengirim pesan
2. **Google Gemini API** - Untuk analisis gambar dan teks makanan
3. **Environment Variables** - Konfigurasi API keys

---

## 2. Testing Strategy

### 2.1 Testing Pyramid

```
        ┌──────────────────┐
        │   E2E Tests      │  ← Sedikit, mahal, lambat
        │   (5-10 tests)   │
        └────────┬─────────┘
                 │
        ┌────────┴─────────┐
        │ Integration Tests│  ← Medium, mock external APIs
        │   (10-15 tests)  │
        └────────┬─────────┘
                 │
        ┌────────┴─────────┐
        │   Unit Tests     │  ← Banyak, cepat, isolated
        │   (20-30 tests)  │
        └──────────────────┘
```

### 2.2 Testing Approach

| Layer | Scope | Mock Strategy |
|-------|-------|---------------|
| Unit | Single function | Mock semua dependency |
| Integration | Multiple modules | Mock external APIs saja |
| E2E | Full system | Gunakan test bot & real APIs |

---

## 3. Unit Testing Plan

### 3.1 Module: `config.py`

| Test Case | Deskripsi | Expected Result |
|-----------|-----------|-----------------|
| `test_load_telegram_token` | Load TELEGRAM_BOT_TOKEN dari env | Token tidak kosong |
| `test_load_gemini_key` | Load GEMINI_API_KEY dari env | Key tidak kosong |
| `test_missing_telegram_token` | Token tidak ada di env | Raise error atau None |
| `test_missing_gemini_key` | Key tidak ada di env | Raise error atau None |

### 3.2 Module: `gemini_service.py`

#### Function: `normalize_response(data: dict) -> dict`

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| `test_normalize_already_normalized` | `{"foods": [...], "total": {...}}` | Return sama tanpa perubahan |
| `test_normalize_old_format` | `{"name": "Nasi", "calories": 200, ...}` | Convert ke format `{foods: [...], total: {...}}` |
| `test_normalize_empty_dict` | `{}` | Handle gracefully |
| `test_normalize_with_error` | `{"error": "..."}` | Return sama tanpa perubahan |
| `test_normalize_missing_fields` | `{"name": "Nasi"}` | Handle missing nutrition fields |

#### Function: `analyze_food_image(image_bytes: bytes) -> dict`

| Test Case | Mock Response | Expected Behavior |
|-----------|---------------|-------------------|
| `test_analyze_image_success` | Valid JSON dengan foods | Return dict dengan foods & total |
| `test_analyze_image_no_food` | `{"error": "Tidak ada makanan"}` | Return error dict |
| `test_analyze_image_invalid_json` | Invalid JSON string | Return error dict |
| `test_analyze_image_api_error` | Raise Exception | Return error dict |
| `test_analyze_image_empty_bytes` | Empty bytes | Handle gracefully |
| `test_analyze_image_multiple_foods` | JSON dengan 3 makanan | Return semua foods dengan total benar |

#### Function: `analyze_food_text(food_description: str) -> dict`

| Test Case | Input | Expected Behavior |
|-----------|-------|-------------------|
| `test_analyze_text_success` | "Nasi goreng 1 piring" | Return dict dengan nutrition |
| `test_analyze_text_empty` | "" | Handle gracefully |
| `test_analyze_text_non_food` | "Ini bukan makanan" | Return appropriate response |
| `test_analyze_text_multiple_items` | "Nasi goreng dan es teh" | Return multiple foods |
| `test_analyze_text_api_error` | Mock API error | Return error dict |

### 3.3 Module: `bot.py`

#### Function: `format_nutrition_response(data: dict) -> str`

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| `test_format_single_food` | 1 food item | Format dengan emoji dan nutrisi |
| `test_format_multiple_foods` | 3 food items | Format semua item + total |
| `test_format_error_response` | `{"error": "..."}` | Pesan error dengan ❌ |
| `test_format_empty_foods` | `{"foods": []}` | Pesan "tidak ada makanan" |
| `test_format_missing_fields` | Food tanpa field lengkap | Handle gracefully |
| `test_format_zero_values` | Semua nilai 0 | Tampilkan 0 dengan benar |
| `test_format_large_numbers` | Kalori 10000+ | Format angka dengan benar |

#### Handler Functions (dengan mock Update & Context)

| Test Case | Trigger | Expected Behavior |
|-----------|---------|-------------------|
| `test_start_command` | `/start` | Kirim welcome message |
| `test_help_command` | `/help` | Kirim help message |
| `test_handle_photo_success` | Photo message | Download, analyze, reply |
| `test_handle_photo_download_error` | Photo (mock download fail) | Error message |
| `test_handle_text_success` | "Nasi goreng" | Analyze dan reply |
| `test_handle_text_command_ignored` | "/unknown" | Tidak diproses |
| `test_handle_text_empty` | "" | Handle gracefully |

---

## 4. Integration Testing Plan

### 4.1 Gemini Service + Bot Handler Integration

| Test Case | Flow | Mock |
|-----------|------|------|
| `test_photo_to_response_flow` | Photo → analyze_food_image → format_nutrition_response | Mock Gemini API |
| `test_text_to_response_flow` | Text → analyze_food_text → format_nutrition_response | Mock Gemini API |
| `test_error_propagation` | API Error → Error response ke user | Mock API error |

### 4.2 Full Message Handler Flow

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Mock       │ →  │  Bot Handlers    │ →  │  Mock Gemini    │
│  Telegram   │    │  (real code)     │    │  Response       │
└─────────────┘    └──────────────────┘    └─────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │  Verify Output  │
                   └─────────────────┘
```

| Test Case | Scenario | Verifikasi |
|-----------|----------|------------|
| `test_full_photo_flow` | Kirim photo → terima nutrition | Response format benar |
| `test_full_text_flow` | Kirim text → terima nutrition | Response format benar |
| `test_multiple_foods_flow` | Photo dengan 3 makanan | Semua item + total |
| `test_non_food_photo_flow` | Photo bukan makanan | Error message ramah |

---

## 5. End-to-End Testing Plan

### 5.1 Prerequisites untuk E2E Testing

1. **Test Bot Token** - Buat bot terpisah untuk testing via @BotFather
2. **Test Gemini API Key** - API key khusus untuk testing
3. **Test User Account** - Telegram account untuk testing
4. **Test Images** - Collection gambar makanan dan non-makanan

### 5.2 E2E Test Scenarios

#### Manual Testing Checklist

| # | Scenario | Steps | Expected Result |
|---|----------|-------|-----------------|
| 1 | Start Command | Kirim `/start` | Welcome message dalam Bahasa Indonesia |
| 2 | Help Command | Kirim `/help` | Instruksi penggunaan |
| 3 | Single Food Photo | Kirim foto nasi goreng | Nutrition info dengan format benar |
| 4 | Multiple Foods Photo | Kirim foto makan siang lengkap | List semua makanan + total |
| 5 | Text Analysis | Kirim "nasi goreng 1 piring" | Nutrition info |
| 6 | Multiple Items Text | Kirim "nasi goreng, es teh, ayam bakar" | List semua + total |
| 7 | Non-Food Photo | Kirim foto pemandangan | Pesan error ramah |
| 8 | Gibberish Text | Kirim "asdfghjkl" | Handle gracefully |
| 9 | Empty Message | Kirim spasi saja | Handle gracefully |
| 10 | Rapid Messages | Kirim 5 pesan berturut-turut | Semua diproses tanpa error |

#### Automated E2E Testing (menggunakan Telethon/Pyrogram)

```python
# Contoh struktur E2E test
class TestBotE2E:
    """
    E2E tests menggunakan real Telegram client
    untuk mengirim pesan ke bot
    """

    async def test_start_command_e2e(self):
        # Kirim /start ke bot
        # Tunggu response
        # Verify response content

    async def test_photo_analysis_e2e(self):
        # Kirim foto makanan
        # Tunggu response (timeout 30s)
        # Verify nutrition data ada
```

### 5.3 Test Data Preparation

#### Test Images Required

| Category | Filename | Description |
|----------|----------|-------------|
| Single Food | `test_nasi_goreng.jpg` | Foto nasi goreng |
| Multiple Foods | `test_lunch_plate.jpg` | Foto makan siang lengkap |
| Non-Food | `test_landscape.jpg` | Foto pemandangan |
| Ambiguous | `test_unclear.jpg` | Foto blur/tidak jelas |
| Edge Case | `test_empty_plate.jpg` | Foto piring kosong |

#### Test Text Inputs

```python
TEST_INPUTS = {
    "single_food": "Nasi goreng 1 piring",
    "multiple_foods": "Nasi goreng, es teh manis, ayam bakar",
    "with_portion": "2 potong ayam goreng",
    "non_food": "Kursi kayu",
    "gibberish": "asdfghjkl12345",
    "empty": "",
    "emoji_only": "🍜🍔🍕",
}
```

---

## 6. Test Dependencies & Setup

### 6.1 Required Packages

Tambahkan ke `requirements.txt` atau buat `requirements-dev.txt`:

```txt
# Testing Framework
pytest==8.0.0
pytest-asyncio==0.23.0
pytest-cov==4.1.0
pytest-mock==3.12.0

# Mocking
responses==0.24.0
aioresponses==0.7.6

# E2E Testing (optional)
telethon==1.34.0
pyrogram==2.0.106

# Code Quality
black==24.1.0
flake8==7.0.0
mypy==1.8.0
```

### 6.2 pytest Configuration

Buat `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
asyncio_mode = auto
addopts = -v --cov=. --cov-report=html --cov-report=term-missing
filterwarnings =
    ignore::DeprecationWarning
```

### 6.3 Environment Setup untuk Testing

Buat `.env.test`:

```env
TELEGRAM_BOT_TOKEN=test_token_12345
GEMINI_API_KEY=test_gemini_key_12345
```

---

## 7. Test File Structure

```
foodtracker/
├── bot.py
├── gemini_service.py
├── config.py
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── .env.test
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   │
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_config.py
│   │   ├── test_gemini_service.py
│   │   └── test_bot.py
│   │
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_message_flow.py
│   │   └── test_error_handling.py
│   │
│   ├── e2e/
│   │   ├── __init__.py
│   │   ├── test_bot_e2e.py
│   │   └── test_scenarios.py
│   │
│   └── fixtures/
│       ├── images/
│       │   ├── test_nasi_goreng.jpg
│       │   ├── test_lunch_plate.jpg
│       │   └── test_landscape.jpg
│       │
│       └── responses/
│           ├── gemini_single_food.json
│           ├── gemini_multiple_foods.json
│           └── gemini_no_food.json
│
└── scripts/
    └── run_tests.sh
```

---

## 8. Contoh Implementasi Test

### 8.1 conftest.py (Shared Fixtures)

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import os

# Set test environment
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
os.environ["GEMINI_API_KEY"] = "test_key"


@pytest.fixture
def sample_single_food_response():
    """Sample Gemini response untuk 1 makanan"""
    return {
        "foods": [
            {
                "name": "Nasi Goreng",
                "calories": 450,
                "protein": 12,
                "carbs": 55,
                "fat": 18,
                "portion": "1 piring"
            }
        ],
        "total": {
            "calories": 450,
            "protein": 12,
            "carbs": 55,
            "fat": 18
        }
    }


@pytest.fixture
def sample_multiple_foods_response():
    """Sample Gemini response untuk multiple makanan"""
    return {
        "foods": [
            {
                "name": "Nasi Putih",
                "calories": 200,
                "protein": 4,
                "carbs": 45,
                "fat": 0,
                "portion": "1 porsi"
            },
            {
                "name": "Ayam Goreng",
                "calories": 300,
                "protein": 25,
                "carbs": 5,
                "fat": 20,
                "portion": "1 potong"
            },
            {
                "name": "Es Teh Manis",
                "calories": 100,
                "protein": 0,
                "carbs": 25,
                "fat": 0,
                "portion": "1 gelas"
            }
        ],
        "total": {
            "calories": 600,
            "protein": 29,
            "carbs": 75,
            "fat": 20
        }
    }


@pytest.fixture
def sample_error_response():
    """Sample error response"""
    return {"error": "Tidak ada makanan yang terdeteksi dalam gambar"}


@pytest.fixture
def sample_old_format_response():
    """Sample old format (sebelum multi-food)"""
    return {
        "name": "Nasi Goreng",
        "calories": 450,
        "protein": 12,
        "carbs": 55,
        "fat": 18,
        "portion": "1 piring"
    }


@pytest.fixture
def mock_telegram_update():
    """Mock Telegram Update object"""
    update = MagicMock()
    update.effective_chat.id = 12345
    update.message.reply_text = AsyncMock()
    update.message.photo = None
    update.message.text = None
    return update


@pytest.fixture
def mock_telegram_context():
    """Mock Telegram Context object"""
    context = MagicMock()
    context.bot.get_file = AsyncMock()
    return context


@pytest.fixture
def sample_image_bytes():
    """Sample image bytes untuk testing"""
    # Minimal valid JPEG header
    return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00'
```

### 8.2 Unit Test: gemini_service.py

```python
# tests/unit/test_gemini_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Import module yang akan ditest
import sys
sys.path.insert(0, '/home/user/foodtracker')
from gemini_service import normalize_response, analyze_food_image, analyze_food_text


class TestNormalizeResponse:
    """Unit tests untuk fungsi normalize_response"""

    def test_normalize_already_normalized(self, sample_single_food_response):
        """Test: data yang sudah dalam format baru tidak diubah"""
        result = normalize_response(sample_single_food_response)
        assert result == sample_single_food_response
        assert "foods" in result
        assert "total" in result

    def test_normalize_old_format(self, sample_old_format_response):
        """Test: convert format lama ke format baru"""
        result = normalize_response(sample_old_format_response)

        assert "foods" in result
        assert "total" in result
        assert len(result["foods"]) == 1
        assert result["foods"][0]["name"] == "Nasi Goreng"
        assert result["total"]["calories"] == 450

    def test_normalize_with_error(self, sample_error_response):
        """Test: response dengan error tidak diubah"""
        result = normalize_response(sample_error_response)
        assert result == sample_error_response
        assert "error" in result

    def test_normalize_empty_dict(self):
        """Test: empty dict handled gracefully"""
        result = normalize_response({})
        # Harusnya tidak crash
        assert isinstance(result, dict)

    def test_normalize_missing_fields(self):
        """Test: format lama dengan field tidak lengkap"""
        incomplete = {"name": "Test Food", "calories": 100}
        result = normalize_response(incomplete)
        assert "foods" in result


class TestAnalyzeFoodImage:
    """Unit tests untuk fungsi analyze_food_image"""

    @pytest.mark.asyncio
    async def test_analyze_image_success(self, sample_image_bytes, sample_single_food_response):
        """Test: analisis gambar berhasil"""
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_single_food_response)

        with patch('gemini_service.model') as mock_model:
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)

            result = await analyze_food_image(sample_image_bytes)

            assert "foods" in result
            assert result["foods"][0]["name"] == "Nasi Goreng"

    @pytest.mark.asyncio
    async def test_analyze_image_no_food(self, sample_image_bytes, sample_error_response):
        """Test: gambar bukan makanan"""
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_error_response)

        with patch('gemini_service.model') as mock_model:
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)

            result = await analyze_food_image(sample_image_bytes)

            assert "error" in result

    @pytest.mark.asyncio
    async def test_analyze_image_invalid_json(self, sample_image_bytes):
        """Test: Gemini return invalid JSON"""
        mock_response = MagicMock()
        mock_response.text = "This is not valid JSON"

        with patch('gemini_service.model') as mock_model:
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)

            result = await analyze_food_image(sample_image_bytes)

            assert "error" in result

    @pytest.mark.asyncio
    async def test_analyze_image_api_error(self, sample_image_bytes):
        """Test: Gemini API throws exception"""
        with patch('gemini_service.model') as mock_model:
            mock_model.generate_content_async = AsyncMock(
                side_effect=Exception("API Error")
            )

            result = await analyze_food_image(sample_image_bytes)

            assert "error" in result

    @pytest.mark.asyncio
    async def test_analyze_image_multiple_foods(self, sample_image_bytes, sample_multiple_foods_response):
        """Test: gambar dengan multiple makanan"""
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_multiple_foods_response)

        with patch('gemini_service.model') as mock_model:
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)

            result = await analyze_food_image(sample_image_bytes)

            assert len(result["foods"]) == 3
            assert result["total"]["calories"] == 600


class TestAnalyzeFoodText:
    """Unit tests untuk fungsi analyze_food_text"""

    @pytest.mark.asyncio
    async def test_analyze_text_success(self, sample_single_food_response):
        """Test: analisis text berhasil"""
        mock_response = MagicMock()
        mock_response.text = json.dumps(sample_single_food_response)

        with patch('gemini_service.model') as mock_model:
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)

            result = await analyze_food_text("Nasi goreng 1 piring")

            assert "foods" in result
            assert result["foods"][0]["name"] == "Nasi Goreng"

    @pytest.mark.asyncio
    async def test_analyze_text_empty(self):
        """Test: text kosong"""
        mock_response = MagicMock()
        mock_response.text = json.dumps({"error": "No food description"})

        with patch('gemini_service.model') as mock_model:
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)

            result = await analyze_food_text("")

            # Should handle gracefully
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_analyze_text_api_error(self):
        """Test: API error"""
        with patch('gemini_service.model') as mock_model:
            mock_model.generate_content_async = AsyncMock(
                side_effect=Exception("API Error")
            )

            result = await analyze_food_text("Nasi goreng")

            assert "error" in result
```

### 8.3 Unit Test: bot.py

```python
# tests/unit/test_bot.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, '/home/user/foodtracker')
from bot import format_nutrition_response, start_command, help_command, handle_photo, handle_text


class TestFormatNutritionResponse:
    """Unit tests untuk fungsi format_nutrition_response"""

    def test_format_single_food(self, sample_single_food_response):
        """Test: format 1 makanan"""
        result = format_nutrition_response(sample_single_food_response)

        assert "✅ Hasil Analisis!" in result
        assert "Nasi Goreng" in result
        assert "450" in result  # calories
        assert "TOTAL" in result

    def test_format_multiple_foods(self, sample_multiple_foods_response):
        """Test: format multiple makanan"""
        result = format_nutrition_response(sample_multiple_foods_response)

        assert "Nasi Putih" in result
        assert "Ayam Goreng" in result
        assert "Es Teh Manis" in result
        assert "TOTAL" in result
        assert "600" in result  # total calories

    def test_format_error_response(self, sample_error_response):
        """Test: format error response"""
        result = format_nutrition_response(sample_error_response)

        assert "❌" in result or "error" in result.lower()

    def test_format_empty_foods(self):
        """Test: foods array kosong"""
        data = {"foods": [], "total": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}}
        result = format_nutrition_response(data)

        # Should handle gracefully
        assert isinstance(result, str)

    def test_format_missing_fields(self):
        """Test: food dengan field tidak lengkap"""
        data = {
            "foods": [{"name": "Test", "calories": 100}],  # missing protein, carbs, fat
            "total": {"calories": 100}
        }
        result = format_nutrition_response(data)

        # Should not crash
        assert "Test" in result


class TestStartCommand:
    """Unit tests untuk /start command"""

    @pytest.mark.asyncio
    async def test_start_command_sends_welcome(self, mock_telegram_update, mock_telegram_context):
        """Test: /start mengirim welcome message"""
        await start_command(mock_telegram_update, mock_telegram_context)

        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args[0][0]

        # Verify welcome message content (Indonesian)
        assert "Halo" in call_args or "selamat" in call_args.lower() or "Selamat" in call_args


class TestHelpCommand:
    """Unit tests untuk /help command"""

    @pytest.mark.asyncio
    async def test_help_command_sends_instructions(self, mock_telegram_update, mock_telegram_context):
        """Test: /help mengirim instruksi"""
        await help_command(mock_telegram_update, mock_telegram_context)

        mock_telegram_update.message.reply_text.assert_called_once()
        call_args = mock_telegram_update.message.reply_text.call_args[0][0]

        # Verify help content
        assert "foto" in call_args.lower() or "photo" in call_args.lower()


class TestHandlePhoto:
    """Unit tests untuk photo handler"""

    @pytest.mark.asyncio
    async def test_handle_photo_success(
        self,
        mock_telegram_update,
        mock_telegram_context,
        sample_single_food_response,
        sample_image_bytes
    ):
        """Test: photo diproses dengan sukses"""
        # Setup mock photo
        mock_photo = MagicMock()
        mock_photo.file_id = "test_file_id"
        mock_telegram_update.message.photo = [mock_photo]

        # Mock file download
        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(sample_image_bytes))
        mock_telegram_context.bot.get_file = AsyncMock(return_value=mock_file)

        with patch('bot.analyze_food_image', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = sample_single_food_response

            await handle_photo(mock_telegram_update, mock_telegram_context)

            # Verify photo was analyzed
            mock_analyze.assert_called_once()
            # Verify response was sent
            mock_telegram_update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_handle_photo_api_error(
        self,
        mock_telegram_update,
        mock_telegram_context,
        sample_image_bytes
    ):
        """Test: handle API error gracefully"""
        mock_photo = MagicMock()
        mock_photo.file_id = "test_file_id"
        mock_telegram_update.message.photo = [mock_photo]

        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(sample_image_bytes))
        mock_telegram_context.bot.get_file = AsyncMock(return_value=mock_file)

        with patch('bot.analyze_food_image', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = {"error": "API Error"}

            await handle_photo(mock_telegram_update, mock_telegram_context)

            # Should still send a response (error message)
            mock_telegram_update.message.reply_text.assert_called()


class TestHandleText:
    """Unit tests untuk text handler"""

    @pytest.mark.asyncio
    async def test_handle_text_success(
        self,
        mock_telegram_update,
        mock_telegram_context,
        sample_single_food_response
    ):
        """Test: text diproses dengan sukses"""
        mock_telegram_update.message.text = "Nasi goreng 1 piring"

        with patch('bot.analyze_food_text', new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = sample_single_food_response

            await handle_text(mock_telegram_update, mock_telegram_context)

            mock_analyze.assert_called_once_with("Nasi goreng 1 piring")
            mock_telegram_update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_handle_text_command_ignored(
        self,
        mock_telegram_update,
        mock_telegram_context
    ):
        """Test: command (/) diabaikan"""
        mock_telegram_update.message.text = "/unknown_command"

        with patch('bot.analyze_food_text', new_callable=AsyncMock) as mock_analyze:
            await handle_text(mock_telegram_update, mock_telegram_context)

            # Should not call analyze for commands
            mock_analyze.assert_not_called()
```

### 8.4 Integration Test

```python
# tests/integration/test_message_flow.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

import sys
sys.path.insert(0, '/home/user/foodtracker')
from bot import handle_photo, handle_text, format_nutrition_response
from gemini_service import analyze_food_image, analyze_food_text


class TestPhotoToResponseFlow:
    """Integration tests: Photo → Analysis → Response"""

    @pytest.mark.asyncio
    async def test_complete_photo_flow(
        self,
        mock_telegram_update,
        mock_telegram_context,
        sample_image_bytes,
        sample_single_food_response
    ):
        """Test: complete flow dari photo sampai response"""
        # Setup
        mock_photo = MagicMock()
        mock_photo.file_id = "test_file_id"
        mock_telegram_update.message.photo = [mock_photo]

        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(sample_image_bytes))
        mock_telegram_context.bot.get_file = AsyncMock(return_value=mock_file)

        # Mock only Gemini API, let the rest run
        with patch('gemini_service.model') as mock_model:
            mock_response = MagicMock()
            mock_response.text = json.dumps(sample_single_food_response)
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)

            await handle_photo(mock_telegram_update, mock_telegram_context)

            # Verify final response format
            call_args = mock_telegram_update.message.reply_text.call_args[0][0]
            assert "✅" in call_args or "Nasi Goreng" in call_args


class TestTextToResponseFlow:
    """Integration tests: Text → Analysis → Response"""

    @pytest.mark.asyncio
    async def test_complete_text_flow(
        self,
        mock_telegram_update,
        mock_telegram_context,
        sample_multiple_foods_response
    ):
        """Test: complete flow dari text sampai response"""
        mock_telegram_update.message.text = "Nasi, ayam goreng, es teh"

        with patch('gemini_service.model') as mock_model:
            mock_response = MagicMock()
            mock_response.text = json.dumps(sample_multiple_foods_response)
            mock_model.generate_content_async = AsyncMock(return_value=mock_response)

            await handle_text(mock_telegram_update, mock_telegram_context)

            # Verify response includes all foods
            call_args = mock_telegram_update.message.reply_text.call_args[0][0]
            assert "TOTAL" in call_args


class TestErrorPropagation:
    """Integration tests: Error handling across modules"""

    @pytest.mark.asyncio
    async def test_api_error_shows_user_friendly_message(
        self,
        mock_telegram_update,
        mock_telegram_context,
        sample_image_bytes
    ):
        """Test: API error menghasilkan pesan error yang ramah"""
        mock_photo = MagicMock()
        mock_photo.file_id = "test_file_id"
        mock_telegram_update.message.photo = [mock_photo]

        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(sample_image_bytes))
        mock_telegram_context.bot.get_file = AsyncMock(return_value=mock_file)

        with patch('gemini_service.model') as mock_model:
            mock_model.generate_content_async = AsyncMock(
                side_effect=Exception("Network Error")
            )

            await handle_photo(mock_telegram_update, mock_telegram_context)

            # Should send error message, not crash
            mock_telegram_update.message.reply_text.assert_called()
            call_args = mock_telegram_update.message.reply_text.call_args[0][0]
            assert "❌" in call_args or "error" in call_args.lower() or "coba lagi" in call_args.lower()
```

### 8.5 E2E Test (Optional - menggunakan real Telegram)

```python
# tests/e2e/test_bot_e2e.py
"""
E2E Tests menggunakan Telethon untuk mengirim pesan ke bot secara langsung.

PREREQUISITE:
1. Set TEST_BOT_USERNAME di .env.test
2. Set TELETHON_API_ID dan TELETHON_API_HASH dari https://my.telegram.org
3. Set TELETHON_SESSION_STRING (bisa generate dengan script terpisah)

JALANKAN:
    pytest tests/e2e/ -v --e2e
"""
import pytest
import asyncio
import os
from pathlib import Path

# Skip jika tidak ada E2E flag
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_E2E_TESTS") != "true",
    reason="E2E tests disabled. Set RUN_E2E_TESTS=true to run."
)

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    TELETHON_AVAILABLE = True
except ImportError:
    TELETHON_AVAILABLE = False


@pytest.fixture
async def telegram_client():
    """Create Telegram client for E2E testing"""
    if not TELETHON_AVAILABLE:
        pytest.skip("Telethon not installed")

    api_id = os.getenv("TELETHON_API_ID")
    api_hash = os.getenv("TELETHON_API_HASH")
    session_string = os.getenv("TELETHON_SESSION_STRING")

    if not all([api_id, api_hash, session_string]):
        pytest.skip("Telethon credentials not configured")

    client = TelegramClient(StringSession(session_string), int(api_id), api_hash)
    await client.start()
    yield client
    await client.disconnect()


@pytest.fixture
def bot_username():
    """Get bot username from environment"""
    username = os.getenv("TEST_BOT_USERNAME", "your_test_bot")
    return username


class TestBotE2E:
    """End-to-end tests dengan real Telegram interaction"""

    @pytest.mark.asyncio
    async def test_start_command_e2e(self, telegram_client, bot_username):
        """E2E: /start command returns welcome message"""
        await telegram_client.send_message(bot_username, "/start")

        # Wait for response
        await asyncio.sleep(3)

        # Get last message from bot
        messages = await telegram_client.get_messages(bot_username, limit=1)
        response = messages[0].text

        assert "Halo" in response or "Selamat" in response

    @pytest.mark.asyncio
    async def test_help_command_e2e(self, telegram_client, bot_username):
        """E2E: /help command returns usage instructions"""
        await telegram_client.send_message(bot_username, "/help")

        await asyncio.sleep(3)

        messages = await telegram_client.get_messages(bot_username, limit=1)
        response = messages[0].text

        assert "foto" in response.lower() or "photo" in response.lower()

    @pytest.mark.asyncio
    async def test_text_analysis_e2e(self, telegram_client, bot_username):
        """E2E: Text food description returns nutrition info"""
        await telegram_client.send_message(bot_username, "Nasi goreng 1 piring")

        # Gemini might take longer
        await asyncio.sleep(10)

        messages = await telegram_client.get_messages(bot_username, limit=1)
        response = messages[0].text

        # Should contain nutrition info
        assert "kalori" in response.lower() or "calories" in response.lower()

    @pytest.mark.asyncio
    async def test_photo_analysis_e2e(self, telegram_client, bot_username):
        """E2E: Food photo returns nutrition analysis"""
        test_image_path = Path(__file__).parent.parent / "fixtures" / "images" / "test_nasi_goreng.jpg"

        if not test_image_path.exists():
            pytest.skip("Test image not found")

        await telegram_client.send_file(bot_username, test_image_path)

        # Photo analysis takes longer
        await asyncio.sleep(15)

        messages = await telegram_client.get_messages(bot_username, limit=1)
        response = messages[0].text

        assert "kalori" in response.lower() or "calories" in response.lower() or "✅" in response
```

---

## 9. CI/CD Integration

### 9.1 GitHub Actions Workflow

Buat `.github/workflows/test.yml`:

```yaml
name: Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run unit tests
        env:
          TELEGRAM_BOT_TOKEN: test_token
          GEMINI_API_KEY: test_key
        run: |
          pytest tests/unit/ -v --cov=. --cov-report=xml

      - name: Run integration tests
        env:
          TELEGRAM_BOT_TOKEN: test_token
          GEMINI_API_KEY: test_key
        run: |
          pytest tests/integration/ -v

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: false

  e2e-test:
    runs-on: ubuntu-latest
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run E2E tests
        env:
          RUN_E2E_TESTS: true
          TELEGRAM_BOT_TOKEN: ${{ secrets.TEST_BOT_TOKEN }}
          GEMINI_API_KEY: ${{ secrets.TEST_GEMINI_KEY }}
          TEST_BOT_USERNAME: ${{ secrets.TEST_BOT_USERNAME }}
          TELETHON_API_ID: ${{ secrets.TELETHON_API_ID }}
          TELETHON_API_HASH: ${{ secrets.TELETHON_API_HASH }}
          TELETHON_SESSION_STRING: ${{ secrets.TELETHON_SESSION_STRING }}
        run: |
          pytest tests/e2e/ -v
```

### 9.2 Test Script

Buat `scripts/run_tests.sh`:

```bash
#!/bin/bash

set -e

echo "🧪 Running Food Tracker Bot Tests"
echo "=================================="

# Load test environment
export $(cat .env.test | xargs)

# Run unit tests
echo ""
echo "📦 Unit Tests"
echo "-------------"
pytest tests/unit/ -v --cov=. --cov-report=term-missing

# Run integration tests
echo ""
echo "🔗 Integration Tests"
echo "--------------------"
pytest tests/integration/ -v

# Optional: Run E2E tests
if [ "$RUN_E2E_TESTS" = "true" ]; then
    echo ""
    echo "🌐 E2E Tests"
    echo "------------"
    pytest tests/e2e/ -v
fi

echo ""
echo "✅ All tests passed!"
```

---

## 10. Prioritas & Timeline

### 10.1 Prioritas Implementasi

| Priority | Test Type | Estimated Tests | Effort |
|----------|-----------|-----------------|--------|
| 🔴 High | Unit: `gemini_service.py` | 10-12 tests | 2-3 jam |
| 🔴 High | Unit: `bot.py` (format_response) | 5-7 tests | 1-2 jam |
| 🟡 Medium | Unit: `bot.py` (handlers) | 6-8 tests | 2-3 jam |
| 🟡 Medium | Integration tests | 5-8 tests | 2-3 jam |
| 🟢 Low | E2E tests | 5-10 tests | 3-4 jam |
| 🟢 Low | CI/CD setup | - | 1-2 jam |

### 10.2 Suggested Implementation Order

```
Week 1:
├── Day 1-2: Setup testing infrastructure
│   ├── Install dependencies
│   ├── Create test directory structure
│   └── Create conftest.py dengan fixtures
│
├── Day 3-4: Unit tests untuk gemini_service.py
│   ├── test_normalize_response
│   ├── test_analyze_food_image
│   └── test_analyze_food_text
│
└── Day 5: Unit tests untuk bot.py
    └── test_format_nutrition_response

Week 2:
├── Day 1-2: Unit tests untuk handlers
│   ├── test_start_command
│   ├── test_help_command
│   ├── test_handle_photo
│   └── test_handle_text
│
├── Day 3: Integration tests
│   ├── test_photo_flow
│   ├── test_text_flow
│   └── test_error_handling
│
└── Day 4-5: E2E tests & CI/CD
    ├── Setup GitHub Actions
    ├── Configure test secrets
    └── E2E test implementation
```

---

## Summary

Plan ini mencakup:

1. **30+ Unit Tests** - Testing fungsi individual dengan mock
2. **10+ Integration Tests** - Testing interaksi antar modul
3. **5-10 E2E Tests** - Testing dengan real Telegram (optional)
4. **CI/CD Pipeline** - Automated testing di GitHub Actions

Dengan mengikuti plan ini, bot akan memiliki **test coverage 80%+** dan confidence tinggi untuk development selanjutnya.

---

*Document Version: 1.0*
*Created: January 2026*
*Last Updated: January 2026*
