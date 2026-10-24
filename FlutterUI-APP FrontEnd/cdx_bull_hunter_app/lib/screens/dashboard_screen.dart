import 'package:flutter/material.dart';
import 'bot_control_screen.dart'; // BotControlScreen ka sahi file path dein

class DashboardScreen extends StatelessWidget {
  final String userEmail;

  const DashboardScreen({Key? key, required this.userEmail}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Bull Hunter Dashboard'),
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
      ),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Welcome Section
            Text(
              'Welcome, $userEmail',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 25),

            // ✅ Bot Control Panel Navigation Card
            Card(
              color: const Color(0xFF1E293B),
              elevation: 4,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
              child: ListTile(
                contentPadding: const EdgeInsets.all(16),
                leading: const CircleAvatar(
                  backgroundColor: Color(0xFF38BDF8),
                  child: Icon(Icons.smart_toy, color: Colors.black),
                ),
                title: const Text(
                  'Bot Control Panel',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                subtitle: const Text(
                  'Manage Start/Stop & Monitor Live Status',
                  style: TextStyle(color: Colors.white70, fontSize: 14),
                ),
                trailing: const Icon(Icons.arrow_forward_ios, color: Colors.white70),
                onTap: () {
                  // Navigate to Bot Control Screen with userEmail
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => BotControlScreen(userEmail: userEmail),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}