// lib/features/profile/restrictions_screen.dart
import 'package:flutter/material.dart';
import 'package:intelligent_menu_app/features/profile/profile_service.dart';

class RestrictionsScreen extends StatefulWidget {
  const RestrictionsScreen({super.key});

  @override
  State<RestrictionsScreen> createState() => _RestrictionsScreenState();
}

class _RestrictionsScreenState extends State<RestrictionsScreen> {
  final List<Map<String, String>> options = [
    {'label': 'ПП', 'image': 'pp.png'},
    {'label': 'Веганство', 'image': 'vegan.png'},
    {'label': 'Вегетарианство', 'image': 'vegetarian.png'},
    {'label': 'Халяль', 'image': 'halal.png'},
    {'label': 'Сыроедение', 'image': 'raw.png'},
    {'label': 'Нет ограничений', 'image': 'no_restriction.png'},
  ];

  final Set<String> _selected = {'Нет ограничений'};

  void _toggleSelection(String label) {
    setState(() {
      if (_selected.contains(label)) {
        _selected.remove(label);
      } else {
        _selected.add(label);
        if (label != 'Нет ограничений' && _selected.contains('Нет ограничений')) {
          _selected.remove('Нет ограничений');
        }
        if (_selected.isEmpty) {
          _selected.add('Нет ограничений');
        }
      }
    });
  }

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
        title: const Text('Ограничения'),
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
        itemCount: options.length,
        itemBuilder: (context, index) {
          final item = options[index];
          final isSelected = _selected.contains(item['label']);
          return GestureDetector(
            onTap: () => _toggleSelection(item['label']!),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    color: isSelected ? Colors.green.withOpacity(0.2) : Colors.grey[200],
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: isSelected ? Colors.green : Colors.transparent,
                      width: 2,
                    ),
                  ),
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
      floatingActionButton: ElevatedButton(
        onPressed: () async {
          await ProfileService.saveRestrictions(_selected.toList());
          Navigator.pushNamed(context, '/recommendations');
        },
        child: const Text('Завершить'),
      ),
    );
  }
}