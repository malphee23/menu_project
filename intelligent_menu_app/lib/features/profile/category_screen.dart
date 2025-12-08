// lib/features/profile/category_screen.dart
import 'package:flutter/material.dart';
import 'package:intelligent_menu_app/features/profile/profile_service.dart';

class CategoryScreen extends StatelessWidget {
  const CategoryScreen({super.key});

  static const List<Map<String, String>> categories = [
    {'label': 'Завтрак', 'image': 'breakfast.png'},
    {'label': 'Обед', 'image': 'lunch.png'},
    {'label': 'Ужин', 'image': 'dinner.png'},
    {'label': 'Свадьба', 'image': 'wedding.png'},
    {'label': 'Романтика', 'image': 'romantic.png'},
    {'label': 'День рождения', 'image': 'birthday.png'},
  ];

  void _exitSession(BuildContext context) {
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
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Категория визита'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.close, color: Colors.grey, size: 30),
            onPressed: () => _exitSession(context),
          ),
        ],
      ),
      body: GridView.builder(
        padding: const EdgeInsets.all(16),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: 2,
          crossAxisSpacing: 16,
          mainAxisSpacing: 16,
        ),
        itemCount: categories.length,
        itemBuilder: (context, index) {
          final item = categories[index];
          return GestureDetector(
            onTap: () async {
              await ProfileService.saveCategory(item['label']!);
              Navigator.pushNamed(context, '/allergies');
            },
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(color: Colors.grey[200], shape: BoxShape.circle),
                  child: ClipOval(
                    child: Image.asset('assets/images/${item['image']}', fit: BoxFit.cover),
                  ),
                ),
                const SizedBox(height: 8),
                Text(item['label']!, textAlign: TextAlign.center, style: const TextStyle(fontSize: 14)),
              ],
            ),
          );
        },
      ),
    );
  }
}