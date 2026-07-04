import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../theme/app_theme.dart';
import '../utils/constants.dart';
import '../utils/helpers.dart';
import 'diagnostic_screen.dart';
import 'study_screen.dart';
import 'test_screen.dart';
import 'progress_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _tab = 0;

  final _screens = const [
    _HomeTab(),
    StudyScreen(),
    TestScreen(),
    ProgressScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final student = auth.student!;
    final lang = student.preferredLanguage;

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const Text('📚 ', style: TextStyle(fontSize: 20)),
            const Text('VidyaBot', style: TextStyle(fontWeight: FontWeight.w800, color: AppTheme.primary)),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: AppTheme.secondary,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                '🔥 ${student.studyStreakDays}',
                style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsScreen())),
          ),
        ],
      ),
      body: _screens[_tab],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _tab,
        onTap: (i) => setState(() => _tab = i),
        items: [
          BottomNavigationBarItem(
            icon: const Icon(Icons.home_outlined),
            activeIcon: const Icon(Icons.home),
            label: lang == 'hi' ? 'होम' : 'Home',
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.menu_book_outlined),
            activeIcon: const Icon(Icons.menu_book),
            label: lang == 'hi' ? 'पढ़ाई' : 'Study',
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.quiz_outlined),
            activeIcon: const Icon(Icons.quiz),
            label: lang == 'hi' ? 'परीक्षा' : 'Test',
          ),
          BottomNavigationBarItem(
            icon: const Icon(Icons.bar_chart_outlined),
            activeIcon: const Icon(Icons.bar_chart),
            label: lang == 'hi' ? 'प्रगति' : 'Progress',
          ),
        ],
      ),
    );
  }
}

class _HomeTab extends StatelessWidget {
  const _HomeTab();

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final student = auth.student!;
    final lang = student.preferredLanguage;
    final examName = getExamDisplayName(student.examTarget);

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  lang == 'hi' ? 'स्वागत है! 👋' : 'Welcome! 👋',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 4),
                Text(
                  lang == 'hi' ? 'लक्ष्य परीक्षा: $examName' : 'Target Exam: $examName',
                  style: TextStyle(color: Colors.grey.shade600),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        if (!student.diagnosticDone) ...[
          Card(
            color: const Color(0xFFFFF8E1),
            child: ListTile(
              leading: const Text('🎯', style: TextStyle(fontSize: 28)),
              title: Text(lang == 'hi' ? 'डायग्नोस्टिक टेस्ट दें' : 'Take Diagnostic Test'),
              subtitle: Text(lang == 'hi' ? 'अपनी कमज़ोरियाँ जानें' : 'Find your weak areas'),
              trailing: const Icon(Icons.arrow_forward_ios, size: 16),
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const DiagnosticScreen())),
            ),
          ),
        ] else ...[
          Row(
            children: [
              _StatCard(label: lang == 'hi' ? 'प्रश्न' : 'Questions',
                        value: '${student.totalQuestionsAttempted}', icon: '✏️'),
              const SizedBox(width: 12),
              _StatCard(label: lang == 'hi' ? 'क्रम' : 'Streak',
                        value: '${student.studyStreakDays}d 🔥', icon: '📅'),
            ],
          ),
          const SizedBox(height: 12),
          if (student.weaknessMap.isNotEmpty) ...[
            Text(
              lang == 'hi' ? '📉 कमज़ोर विषय' : '📉 Focus Areas',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            ...student.weaknessMap.take(3).map((w) => Card(
              child: ListTile(
                leading: Text(scoreEmoji(w.scorePct), style: const TextStyle(fontSize: 20)),
                title: Text(w.topic),
                subtitle: Text(w.subject),
                trailing: Text('${(w.scorePct * 100).toStringAsFixed(0)}%',
                    style: TextStyle(color: scoreColor(w.scorePct), fontWeight: FontWeight.bold)),
              ),
            )),
          ],
        ],
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: ElevatedButton.icon(
              onPressed: () {},
              icon: const Icon(Icons.menu_book, size: 18),
              label: Text(lang == 'hi' ? 'पढ़ें' : 'Study'),
            )),
            const SizedBox(width: 12),
            Expanded(child: OutlinedButton.icon(
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const DiagnosticScreen())),
              icon: const Icon(Icons.quiz, size: 18),
              label: Text(lang == 'hi' ? 'टेस्ट दें' : 'Take Test'),
            )),
          ],
        ),
      ],
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label, value, icon;
  const _StatCard({required this.label, required this.value, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Text(icon, style: const TextStyle(fontSize: 28)),
              const SizedBox(height: 4),
              Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18)),
              Text(label, style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
            ],
          ),
        ),
      ),
    );
  }
}
