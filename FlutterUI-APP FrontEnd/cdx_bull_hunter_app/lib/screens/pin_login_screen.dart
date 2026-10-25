import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart'; // 🔑 Persistent session ke liye zaroori package
import 'dashboard_screen.dart';

class PinLoginScreen extends StatefulWidget {
  final String email;
  const PinLoginScreen({Key? key, required this.email}) : super(key: key);

  @override
  State<PinLoginScreen> createState() => _PinLoginScreenState();
}

class _PinLoginScreenState extends State<PinLoginScreen> {
  final TextEditingController _pinController = TextEditingController();
  bool _isLoading = false;

  final String baseUrl = "https://bull-hunter-bot-gbhv9-5.onrender.com";

  Future<void> _verifyPin() async {
    final pin = _pinController.text.trim();
    if (pin.length < 4) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('कृपया वैध 4 या 6-डिजिट का PIN दर्ज करें'), backgroundColor: Colors.red),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/verify-pin'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': widget.email,
          'pin': pin,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        // 🔑 STAGE 1: पिन सही होने पर भी सेशन को SharedPreferences में सुरक्षित रखें
        SharedPreferences prefs = await SharedPreferences.getInstance();
        await prefs.setString('logged_in_email', widget.email.trim().toLowerCase());

        if (!mounted) return;
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(
            builder: (context) => DashboardScreen(userEmail: widget.email),
          ),
          (route) => false,
        );
      } else {
        throw Exception(data['detail'] ?? 'गलत PIN दर्ज किया गया है');
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: ${e.toString()}'), backgroundColor: Colors.red),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0F1D),
      appBar: AppBar(
        title: const Text('Enter Secure PIN', style: TextStyle(color: Colors.white, fontSize: 18)),
        backgroundColor: const Color(0xFF1E293B),
        iconTheme: const IconThemeData(color: Colors.cyanAccent),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 20),
            const Text(
              'सुरक्षा पिन दर्ज करें',
              style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            Text(
              'खाते को एक्सेस करने के लिए अपना 4 या 6-डिजिट का App PIN दर्ज करें (${widget.email})।',
              style: const TextStyle(color: Colors.white70, fontSize: 13),
            ),
            const SizedBox(height: 30),
            TextField(
              controller: _pinController,
              keyboardType: TextInputType.number,
              obscureText: true,
              maxLength: 6,
              style: const TextStyle(color: Colors.white, fontSize: 22, letterSpacing: 8),
              decoration: InputDecoration(
                labelText: 'App PIN',
                labelStyle: const TextStyle(color: Colors.white54),
                prefixIcon: const Icon(Icons.lock, color: Colors.cyanAccent),
                filled: true,
                fillColor: const Color(0xFF1E293B),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: BorderSide.none,
                ),
                counterText: '',
              ),
            ),
            const SizedBox(height: 30),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _verifyPin,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.cyanAccent,
                  foregroundColor: Colors.black,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: _isLoading
                    ? const CircularProgressIndicator(color: Colors.black)
                    : const Text(
                        'LOGIN TO DASHBOARD',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}