// lib/main.dart
import 'package:flutter/material.dart';

// Auth
import 'package:intelligent_menu_app/features/auth/guest_or_login_screen.dart';
import 'package:intelligent_menu_app/features/auth/login_screen.dart';
import 'package:intelligent_menu_app/features/auth/register_screen.dart';

// Profile & other screens (same as before)
import 'package:intelligent_menu_app/features/profile/date_screen.dart';
import 'package:intelligent_menu_app/features/profile/category_screen.dart';
import 'package:intelligent_menu_app/features/profile/allergies_screen.dart';
import 'package:intelligent_menu_app/features/profile/restrictions_screen.dart';
import 'package:intelligent_menu_app/features/recommendations/recommendations_screen.dart';
import 'package:intelligent_menu_app/features/cart/cart_screen.dart';
import 'package:intelligent_menu_app/features/order/order_status_screen.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Интеллектуальное меню',
      theme: ThemeData(useMaterial3: true),
      home: const GuestOrLoginScreen(), // ← НОВЫЙ СТАРТОВЫЙ ЭКРАН
      routes: {
        '/welcome': (context) => const GuestOrLoginScreen(),
        '/login': (context) => const LoginScreen(),
        '/register': (context) => const RegisterScreen(),
        '/date': (context) => const DateScreen(),
        '/category': (context) => const CategoryScreen(),
        '/allergies': (context) => const AllergiesScreen(),
        '/restrictions': (context) => const RestrictionsScreen(),
        '/recommendations': (context) => const RecommendationsScreen(),
        '/cart': (context) => const CartScreen(),
        '/order_status': (context) => const OrderStatusScreen(),
      },
    );
  }
}