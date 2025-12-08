// lib/features/recommendations/recommendations_screen.dart
import 'package:flutter/material.dart';
import 'package:intelligent_menu_app/features/cart/cart_screen.dart';
import 'package:intelligent_menu_app/features/order/order_status_screen.dart';

class RecommendationsScreen extends StatelessWidget {
  static const String routeName = '/recommendations';

  const RecommendationsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Рекомендации'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.close, color: Colors.grey, size: 30),
            onPressed: () {
              showDialog(
                context: context,
                builder: (context) => AlertDialog(
                  title: const Text('Завершить сеанс?'),
                  content: const Text('Все несохранённые данные будут потеряны.'),
                  actions: [
                    TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Отмена')),
                    TextButton(
                      onPressed: () {
                        Navigator.of(context).pop();
                        Navigator.of(context).pushNamedAndRemoveUntil('/login', (route) => false);
                      },
                      child: const Text('Выйти'),
                    ),
                  ],
                ),
              );
            },
          ),
          PopupMenuButton<String>(
            onSelected: (result) {
              if (result == 'cart') {
                Navigator.pushNamed(context, '/cart');
              } else if (result == 'order_status') {
                Navigator.pushNamed(context, '/order_status');
              }
            },
            itemBuilder: (context) => const [
              PopupMenuItem(value: 'cart', child: Text('Корзина')),
              PopupMenuItem(value: 'order_status', child: Text('Статус заказа')),
            ],
          ),
        ],
      ),
      body: const Center(child: Text('Здесь будут рекомендации')),
    );
  }
}