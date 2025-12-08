// lib/features/order/order_status_screen.dart
import 'package:flutter/material.dart';

class OrderStatusScreen extends StatelessWidget {
  static const String routeName = '/order_status';
  const OrderStatusScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Статус заказа'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.close, color: Colors.grey, size: 30),
            onPressed: () {
              Navigator.pushNamedAndRemoveUntil(context, '/login', (route) => false);
            },
          ),
        ],
      ),
      body: const Center(child: Text('Статус заказа')),
    );
  }
}