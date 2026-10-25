import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dashboard_screen.dart';

class SetPinScreen extends StatefulWidget {
  final String email;
  const SetPinScreen({Key? key, required this.email}) : super(key: key);

  @override
  State<SetPinScreen> createState() => _SetPinScreenState();
}

class _SetPinScreenState extends State<SetPinScreen> {
  final TextEditingController _pinController = TextEditingController();
  bool _isLoading = false;

  final String baseUrl = "https://bull-hunter-bot-gbhv9-5.onrender.com";

  Future<void> _setPin() async {
    final pin = _pinController.text.trim();
    if (pin.length < 4) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('कम से कम 4-डिजिट का PIN आवश्यक है'), backgroundColor: Colors.red),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/auth/set-pin'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'email': widget.email,
          'pin': pin,
        }),
      );

      final data = jsonDecode(response.body);

      if (response.statusCode == 200) {
        if (!mounted) return;
        Navigator.pushAndRemoveUntil(
          context,
          MaterialPageRoute(
            builder: (context) => DashboardScreen(userEmail: widget.email),
          ),
          (route) => false,
        );
      } else {
        throw Exception(data['detail'] ?? 'PIN सेट करने में विफल');
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
        title: const Text('Create App PIN', style: TextStyle(color: Colors.white, fontSize: 18)),
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
              'नया सुरक्षा पिन सेट करें',
              style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 10),
            Text(
              'आप पहले से रजिस्टर्ड हैं लेकिन ऐप के लिए कोई PIN सेट नहीं है। भविष्य के लॉगिन के लिए एक नया PIN बनाएं (${widget.email})।',
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
                labelText: 'New App PIN',
                labelStyle: const TextStyle(color: Colors.white54),
                prefixIcon: const Icon(Icons.lock_outline, color: Colors.cyanAccent),
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
                onPressed: _isLoading ? null : _setPin,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.cyanAccent,
                  foregroundColor: Colors.black,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: _isLoading
                    ? const CircularProgressIndicator(color: Colors.black)
                    : const Text(
                        'SAVE PIN & CONTINUE',
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