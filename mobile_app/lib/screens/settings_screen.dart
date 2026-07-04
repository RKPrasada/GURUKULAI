import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';
import '../utils/constants.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late TextEditingController _apiUrlController;

  @override
  void initState() {
    super.initState();
    _apiUrlController = TextEditingController(text: dotenv.env['API_BASE_URL'] ?? 'http://localhost:8000');
  }

  @override
  void dispose() {
    _apiUrlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final student = auth.student;
    final lang = student?.preferredLanguage ?? 'en';

    return Scaffold(
      appBar: AppBar(title: Text(lang == 'hi' ? 'सेटिंग्स' : 'Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // API Configuration
          _SectionHeader(title: lang == 'hi' ? '🔌 API कॉन्फ़िगरेशन' : '🔌 API Configuration'),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(lang == 'hi' ? 'API URL' : 'API Base URL',
                      style: const TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 8),
                  TextField(controller: _apiUrlController,
                      decoration: const InputDecoration(hintText: 'http://10.0.2.2:8000')),
                  const SizedBox(height: 8),
                  const Text('• Android emulator: http://10.0.2.2:8000\n'
                      '• iOS simulator: http://localhost:8000\n'
                      '• Physical device: http://<your-computer-ip>:8000',
                      style: TextStyle(fontSize: 12, color: Colors.grey)),
                  const SizedBox(height: 12),
                  ElevatedButton(
                    onPressed: () {
                      dotenv.env['API_BASE_URL'] = _apiUrlController.text;
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('✅ API URL updated'), backgroundColor: AppTheme.successColor),
                      );
                    },
                    child: const Text('Save'),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 16),

          // Language & Exam
          if (student != null) ...[
            _SectionHeader(title: lang == 'hi' ? '📚 अध्ययन सेटिंग्स' : '📚 Study Preferences'),
            Card(
              child: Column(
                children: [
                  ListTile(
                    title: Text(lang == 'hi' ? 'भाषा' : 'Language'),
                    trailing: DropdownButton<String>(
                      value: student.preferredLanguage,
                      underline: const SizedBox(),
                      items: AppConstants.languageKeys.asMap().entries.map((e) =>
                        DropdownMenuItem(value: e.value, child: Text(AppConstants.languages[e.key]))
                      ).toList(),
                      onChanged: (v) async {
                        if (v != null) {
                          await ApiService().updateExam(student.studentId, student.examTarget, v);
                          await auth.refreshStudent();
                        }
                      },
                    ),
                  ),
                  const Divider(height: 0),
                  ListTile(
                    title: Text(lang == 'hi' ? 'परीक्षा' : 'Target Exam'),
                    trailing: Text(AppConstants.examKeys.contains(student.examTarget)
                        ? AppConstants.supportedExams[AppConstants.examKeys.indexOf(student.examTarget)]
                        : student.examTarget),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            _SectionHeader(title: lang == 'hi' ? '👤 अकाउंट' : '👤 Account'),
            Card(
              child: Column(
                children: [
                  ListTile(
                    leading: const CircleAvatar(child: Icon(Icons.person)),
                    title: Text(student.displayName),
                    subtitle: Text(student.username != null
                        ? '@${student.username}'
                        : student.studentId.substring(0, 16) + '...'),
                  ),
                  const Divider(height: 0),
                  ListTile(
                    leading: const Icon(Icons.delete_outline, color: Colors.red),
                    title: Text(lang == 'hi' ? 'डेटा साफ़ करें' : 'Clear Local Data'),
                    onTap: () => showDialog(
                      context: context,
                      builder: (ctx) => AlertDialog(
                        title: const Text('Clear Data?'),
                        content: const Text('This will log you out and clear all local data.'),
                        actions: [
                          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
                          TextButton(
                            onPressed: () { Navigator.pop(ctx); auth.logout(); },
                            child: const Text('Clear', style: TextStyle(color: Colors.red)),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const Divider(height: 0),
                  ListTile(
                    leading: const Icon(Icons.logout, color: AppTheme.primary),
                    title: Text(lang == 'hi' ? 'लॉगआउट' : 'Logout'),
                    onTap: auth.logout,
                  ),
                ],
              ),
            ),
          ],

          const SizedBox(height: 16),

          _SectionHeader(title: lang == 'hi' ? 'ℹ️ के बारे में' : 'ℹ️ About'),
          Card(
            child: Column(
              children: [
                const ListTile(title: Text('Gurukul AI'), subtitle: Text('Version 1.0.0'), leading: Text('🎓', style: TextStyle(fontSize: 28))),
                const Divider(height: 0),
                const ListTile(title: Text('Stack'), subtitle: Text('Flutter · FastAPI · OpenRouter · RRB NTPC · NDA · JEE · NEET')),
                const Divider(height: 0),
                const ListTile(
                  title: Text('GitHub'),
                  subtitle: Text('github.com/RKPrasada/GURUKULAI'),
                  leading: Icon(Icons.code),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader({required this.title});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text(title, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15, color: AppTheme.primary)),
    );
  }
}
