import 'package:flutter/material.dart';
import 'package:intelligent_menu_app/features/profile/profile_screen.dart';

class CategorySelectionScreen extends StatelessWidget {
  const CategorySelectionScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Выберите категорию визита')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _buildCategoryButton(context, 'Завтрак'),
            _buildCategoryButton(context, 'Обед'),
            _buildCategoryButton(context, 'Ужин'),
            _buildCategoryButton(context, 'Перекус'),
            _buildCategoryButton(context, 'Другое'),
          ],
        ),
      ),
    );
  }

  Widget _buildCategoryButton(BuildContext context, String label) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 24),
      child: SizedBox(
        width: 200,
        height: 50,
        child: ElevatedButton(
          onPressed: () {
            // Передаём выбранную категорию в профиль
            Navigator.push(
              context,
              MaterialPageRoute(
                builder: (context) => ProfileScreen(category: label),
              ),
            );
          },
          child: Text(label, style: const TextStyle(fontSize: 18)),
        ),
      ),
    );
  }
}