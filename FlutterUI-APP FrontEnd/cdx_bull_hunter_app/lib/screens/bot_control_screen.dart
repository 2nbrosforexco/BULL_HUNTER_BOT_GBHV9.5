import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:web_socket_channel/web_socket_channel.dart';
import '../widgets/wallet_positions_widget.dart'; // ✅ Wallet & Positions widget import kiya

class BotControlScreen extends StatefulWidget {
  final String userEmail;

  const BotControlScreen({Key? key, required this.userEmail}) : super(key: key);

  @override
  State<BotControlScreen> createState() => _BotControlScreenState();
}

class _BotControlScreenState extends State<BotControlScreen> {
  bool _isBotRunning = false;
  bool _isLoading = false;
  WebSocketChannel? _channel;
  String _botStatusText = "Connecting to Bot...";

  @override
  void initState() {
    super.initState();
    _connectWebSocketStatus();
  }

  // WebSocket connection for real-time status updates
  void _connectWebSocketStatus() {
    final wsUrl = Uri.parse('wss://bull-hunter-bot-gbhv9-5.onrender.com/ws/bot-status/${widget.userEmail}');
    _channel = WebSocketChannel.connect(wsUrl);

    _channel!.stream.listen((message) {
      final data = jsonDecode(message);
      setState(() {
        if (data.containsKey('status')) {
          _isBotRunning = data['status'] == 'running';
          _botStatusText = _isBotRunning ? "Bot is Running 🚀" : "Bot is Stopped ⏹️";
        }
      });
    }, onError: (error) {
      setState(() {
        _botStatusText = "Connection Error";
      });
    });
  }

  // Function to Start or Stop the Bot via Backend API
  Future<void> _toggleBot(bool start) async {
    setState(() => _isLoading = true);
    
    final endpoint = start ? 'start-bot' : 'stop-bot';
    final url = Uri.parse('https://bull-hunter-bot-gbhv9-5.onrender.com/$endpoint');

    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'user_email': widget.userEmail}),
      );

      if (response.statusCode == 200) {
        setState(() {
          _isBotRunning = start;
          _botStatusText = _isBotRunning ? "Bot is Running 🚀" : "Bot is Stopped ⏹️";
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(start ? 'Bot successfully started!' : 'Bot stopped successfully.'),
            backgroundColor: start ? Colors.green : Colors.red,
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Failed to update bot state. Please try again.')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Network Error: $e')),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  void dispose() {
    _channel?.sink.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Bull Hunter Control Panel'),
        backgroundColor: const Color(0xFF1E293B),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Status Card
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: _isBotRunning ? Colors.greenAccent : Colors.redAccent,
                  width: 1.5,
                ),
              ),
              child: Column(
                children: [
                  const Text(
                    'Current Bot Status',
                    style: TextStyle(color: Colors.white70, fontSize: 16),
                  ),
                  const SizedBox(height: 10),
                  Text(
                    _botStatusText,
                    style: TextStyle(
                      color: _isBotRunning ? Colors.greenAccent : Colors.redAccent,
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 25),

            // Control Buttons
            if (_isLoading)
              const Center(child: CircularProgressIndicator(color: Color(0xFF38BDF8)))
            else
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: _isBotRunning ? null : () => _toggleBot(true),
                      icon: const Icon(Icons.play_arrow),
                      label: const Text('START BOT'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                    ),
                  ),
                  const SizedBox(width: 15),
                  Expanded(
                    child: ElevatedButton.icon(
                      onPressed: !_isBotRunning ? null : () => _toggleBot(false),
                      icon: const Icon(Icons.stop),
                      label: const Text('STOP BOT'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.red,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                    ),
                  ),
                ],
              ),
            const SizedBox(height: 30),

            // ✅ Wallet & Open Positions Widget Integration
            WalletPositionsWidget(userEmail: widget.userEmail),
          ],
        ),
      ),
    );
  }
}