// lib/features/profile/style_screen.dart
import 'package:flutter/material.dart';
import 'package:intelligent_menu_app/features/profile/profile_service.dart';

class StyleScreen extends StatefulWidget {
  const StyleScreen({super.key});

  @override
  State<StyleScreen> createState() => _StyleScreenState();
}

class _StyleScreenState extends State<StyleScreen> {
  String _selected = 'Быстро';

  static const List<String> options = [
    'Быстро',
    'Романтический ужин',
    'Дружеская вечеринка',
    'Деловой обед',
    'Семейный ужин',
    'Соло',
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Стиль приёма пищи')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            const Text('Выберите стиль:', style: TextStyle(fontSize: 18)),
            const SizedBox(height: 20),
            DropdownButtonFormField<String>(
              value: _selected,
              onChanged: (value) => setState(() => _selected = value!),
              items: options.map((e) => DropdownMenuItem(value: e, child: Text(e))).toList(),
            ),
            const Spacer(),
            ElevatedButton(
              onPressed: () async {
                await ProfileService.saveStyle(_selected);
                // Готово! Можно переходить к рекомендациям
                Navigator.pushReplacementNamed(context, '/recommendations');
              },
              child: const Text('Завершить профиль'),
            ),
          ],
        ),
      ),
    );
  }
}