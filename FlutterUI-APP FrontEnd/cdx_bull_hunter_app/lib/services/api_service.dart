import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';

class ApiService {
  // Apne Render wale live backend ka URL yahan hai[cite: 9]
  static const String baseUrl = "https://bull-hunter-bot-gbhv9-5.onrender.com";

  // 1. User Register & API Keys Save (Backend ke mutabiq corrected fields)
  static Future<Map<String, dynamic>> registerUser({
    required String fullName,
    required String email,
    required String phoneNumber,
    required String apiKey,
    required String secretKey,
    String telegramToken = "",
    String telegramChatId = "",
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/user/register'),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "full_name": fullName,
          "email": email,
          "phone_number": phoneNumber,
          "coindcx_api_key": apiKey,
          "coindcx_secret": secretKey,
          "telegram_token": telegramToken,
          "telegram_chat_id": telegramChatId,
        }),
      );
      return jsonDecode(response.body);
    } catch (e) {
      return {"status": "error", "message": e.toString()};
    }
  }

  // 2. Fetch CoinDCX Futures Balance[cite: 9]
  static Future<Map<String, dynamic>> getFuturesBalance(
      String apiKey, String secretKey) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/coindcx/futures/balance'),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({
          "api_key": apiKey,
          "secret_key": secretKey,
        }),
      );
      return jsonDecode(response.body);
    } catch (e) {
      return {"status": "error", "message": e.toString()};
    }
  }

  // 3. WebSocket Connection Helper (Agar aap WebSocket ko bhi service mein rakhna chahein)
  static WebSocketChannel connectWebSocket(String email) {
    final wsUrl = Uri.parse('wss://bull-hunter-bot-gbhv9-5.onrender.com/ws/bot-status/$email');
    return WebSocketChannel.connect(wsUrl);
  }
}