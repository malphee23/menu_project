// lib/features/profile/date_screen.dart
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:intelligent_menu_app/features/profile/profile_service.dart';

class DateScreen extends StatefulWidget {
  const DateScreen({super.key});

  @override
  State<DateScreen> createState() => _DateScreenState();
}

class _DateScreenState extends State<DateScreen> {
  late DateTime _selectedDate;

  @override
  void initState() {
    _selectedDate = DateTime.now();
    super.initState();
  }

  void _exitSession() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Завершить сеанс?'),
        content: const Text('Все несохранённые данные будут потеряны.'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('Отмена')),
          TextButton(
            onPressed: () async {
              final prefs = await SharedPreferences.getInstance();
              final isGuest = prefs.getBool('is_guest') ?? false;
              await prefs.clear();
              Navigator.pushNamedAndRemoveUntil(
                context,
                isGuest ? '/welcome' : '/login',
                (route) => false,
              );
            },
            child: const Text('Выйти'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<bool>(
      future: _checkIfGuest(),
      builder: (context, snapshot) {
        final isGuest = snapshot.data ?? false;
        return Scaffold(
          appBar: AppBar(
            title: const Text('Дата рождения'),
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () {
                if (isGuest) {
                  // Гость → возврат к выбору
                  Navigator.pushNamedAndRemoveUntil(context, '/welcome', (route) => false);
                } else {
                  // Зарегистрированный — обычно не должен попадать сюда напрямую,
                  // но на всякий случай — просто pop
                  Navigator.maybePop(context);
                }
              },
            ),
            actions: [
              IconButton(
                icon: const Icon(Icons.close, color: Colors.grey, size: 30),
                onPressed: _exitSession,
              ),
            ],
          ),
          body: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              children: [
                CalendarDatePicker(
                  firstDate: DateTime(1900),
                  lastDate: DateTime.now(),
                  currentDate: _selectedDate,
                  initialDate: _selectedDate,
                  onDateChanged: (date) {
                    setState(() => _selectedDate = date);
                  },
                ),
                const Spacer(),
                ElevatedButton(
                  onPressed: () async {
                    await ProfileService.saveBirthDate(_selectedDate);
                    Navigator.pushNamed(context, '/category');
                  },
                  child: const Text('Далее'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Future<bool> _checkIfGuest() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool('is_guest') ?? false;
  }
}