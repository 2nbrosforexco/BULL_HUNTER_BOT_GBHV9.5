import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

class WalletPositionsWidget extends StatefulWidget {
  final String userEmail;

  const WalletPositionsWidget({Key? key, required this.userEmail}) : super(key: key);

  @override
  State<WalletPositionsWidget> createState() => _WalletPositionsWidgetState();
}

class _WalletPositionsWidgetState extends State<WalletPositionsWidget> {
  WebSocketChannel? _channel;
  double _walletBalance = 0.0;
  List<dynamic> _openPositions = [];

  @override
  void initState() {
    super.initState();
    _connectWebSocket();
  }

  // WebSocket connection for real-time wallet and positions sync
  void _connectWebSocket() {
    final wsUrl = Uri.parse('wss://bull-hunter-bot-gbhv9-5.onrender.com/ws/bot-status/${widget.userEmail}');
    _channel = WebSocketChannel.connect(wsUrl);

    _channel!.stream.listen((message) {
      final data = jsonDecode(message);
      setState(() {
        if (data.containsKey('wallet_balance')) {
          _walletBalance = (data['wallet_balance'] as num).toDouble();
        }
        if (data.containsKey('open_positions')) {
          _openPositions = data['open_positions'] ?? [];
        }
      });
    }, onError: (error) {
      print("WebSocket Error in Wallet/Positions: $error");
    });
  }

  @override
  void dispose() {
    _channel?.sink.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // 💰 Wallet Balance Card
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: const Color(0xFF1E293B),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFF38BDF8), width: 1),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Futures Wallet Balance',
                style: TextStyle(color: Colors.white70, fontSize: 14),
              ),
              const SizedBox(height: 8),
              Text(
                '₹${_walletBalance.toStringAsFixed(2)}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 26,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),

        // 📈 Active Open Positions Section Title
        const Text(
          'Active Open Positions',
          style: TextStyle(
            color: Colors.white,
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 10),

        // 📋 Open Positions List View
        _openPositions.isEmpty
            ? Container(
                padding: const EdgeInsets.all(20),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: const Color(0xFF1E293B),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Text(
                  'No active open positions right now.',
                  style: TextStyle(color: Colors.white54, fontSize: 14),
                ),
              )
            : ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _openPositions.length,
                itemBuilder: (context, index) {
                  final position = _openPositions[index];
                  final symbol = position['symbol'] ?? 'UNKNOWN';
                  final side = position['side'] ?? 'BUY';
                  final entryPrice = (position['entry_price'] as num?)?.toDouble() ?? 0.0;
                  final pnl = (position['pnl'] as num?)?.toDouble() ?? 0.0;

                  return Card(
                    color: const Color(0xFF1E293B),
                    margin: const EdgeInsets.only(bottom: 10),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: ListTile(
                      title: Text(
                        '$symbol ($side)',
                        style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      subtitle: Text(
                        'Entry Price: ₹$entryPrice',
                        style: const TextStyle(color: Colors.white70),
                      ),
                      trailing: Text(
                        'PnL: ₹${pnl.toStringAsFixed(2)}',
                        style: TextStyle(
                          color: pnl >= 0 ? Colors.greenAccent : Colors.redAccent,
                          fontWeight: FontWeight.bold,
                          fontSize: 15,
                        ),
                      ),
                    ),
                  );
                },
              ),
      ],
    );
  }
}