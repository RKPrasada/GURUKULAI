import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../providers/auth_provider.dart';
import '../theme/app_theme.dart';
import '../utils/helpers.dart';
import 'progress_screen.dart';
import 'settings_screen.dart';
import 'study_plan_screen.dart';

class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final student = auth.student!;
    final lang = student.preferredLanguage;
    final examName = getExamDisplayName(student.examTarget);

    return Scaffold(
      appBar: AppBar(
        title: Text(lang == 'hi' ? 'प्रोफ़ाइल' : 'Profile'),
      ),
      body: ListView(
        children: [
          // ── Profile card ────────────────────────────────────────────────────
          Container(
            margin: const EdgeInsets.all(16),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [AppTheme.primary, Color(0xFF7C3AED)],
                begin: Alignment.topLeft, end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(children: [
              CircleAvatar(
                radius: 32,
                backgroundColor: Colors.white.withOpacity(0.2),
                child: Text(
                  ((student.name?.isNotEmpty ?? false) ? student.name![0] : 'S').toUpperCase(),
                  style: const TextStyle(fontSize: 28, fontWeight: FontWeight.w800, color: Colors.white),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(
                    (student.name?.isNotEmpty ?? false) ? student.name! : 'Student',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 18),
                  ),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(examName,
                        style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w600)),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '🔥 ${student.studyStreakDays} ${lang == 'hi' ? 'दिन की लकीर' : 'day streak'}',
                    style: const TextStyle(color: Colors.white70, fontSize: 13),
                  ),
                ]),
              ),
            ]),
          ),

          // ── Learning ────────────────────────────────────────────────────────
          _SectionHeader(label: lang == 'hi' ? 'सीखना' : 'Learning'),
          _Tile(
            icon: Icons.bar_chart,
            color: Colors.indigo,
            title: lang == 'hi' ? 'मेरी प्रगति' : 'My Progress',
            subtitle: lang == 'hi' ? 'स्कोर, कमज़ोरी मानचित्र, सत्र इतिहास' : 'Scores, weakness map, session history',
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ProgressScreen())),
          ),
          _Tile(
            icon: Icons.calendar_month,
            color: AppTheme.primary,
            title: lang == 'hi' ? 'आज की पढ़ाई' : "Today's Study Plan",
            subtitle: lang == 'hi' ? 'Dabbu की दैनिक योजना देखें' : 'View your Dabbu-powered daily schedule',
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const StudyPlanScreen())),
          ),

          // ── Support ─────────────────────────────────────────────────────────
          _SectionHeader(label: lang == 'hi' ? 'सहायता' : 'Support'),
          _Tile(
            icon: Icons.feedback_outlined,
            color: Colors.teal,
            title: lang == 'hi' ? 'फ़ीडबैक दें' : 'Give Feedback',
            subtitle: lang == 'hi' ? 'हमें बताएं कि आपको क्या पसंद है' : 'Tell us what you like or want improved',
            onTap: () => _showFeedbackSheet(context, lang),
          ),
          _Tile(
            icon: Icons.mail_outline,
            color: Colors.orange,
            title: lang == 'hi' ? 'हमसे संपर्क करें' : 'Contact Us',
            subtitle: 'rkprasada@gmail.com',
            onTap: () => _launchEmail(),
          ),
          _Tile(
            icon: Icons.help_outline,
            color: Colors.blue,
            title: lang == 'hi' ? 'सहायता और अक्सर पूछे गए प्रश्न' : 'Help & FAQ',
            subtitle: lang == 'hi' ? 'सामान्य प्रश्नों के उत्तर' : 'Answers to common questions',
            onTap: () => _showHelpSheet(context, lang),
          ),

          // ── Account ─────────────────────────────────────────────────────────
          _SectionHeader(label: lang == 'hi' ? 'खाता' : 'Account'),
          _Tile(
            icon: Icons.settings_outlined,
            color: Colors.grey,
            title: lang == 'hi' ? 'सेटिंग्स' : 'Settings',
            subtitle: lang == 'hi' ? 'भाषा, परीक्षा लक्ष्य, सर्वर URL' : 'Language, exam target, server URL',
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsScreen())),
          ),
          _Tile(
            icon: Icons.logout,
            color: Colors.red,
            title: lang == 'hi' ? 'लॉग आउट' : 'Log Out',
            subtitle: lang == 'hi' ? 'अपने खाते से बाहर निकलें' : 'Sign out of your account',
            onTap: () => _confirmLogout(context, auth, lang),
          ),

          const SizedBox(height: 32),
          Center(
            child: Text(
              'Gurukul AI · v1.0.0',
              style: TextStyle(color: Colors.grey.shade400, fontSize: 12),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  void _showFeedbackSheet(BuildContext context, String lang) {
    final controller = TextEditingController();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
          left: 20, right: 20, top: 24,
          bottom: MediaQuery.of(ctx).viewInsets.bottom + 24,
        ),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(
            lang == 'hi' ? 'फ़ीडबैक दें' : 'Share Feedback',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          Text(
            lang == 'hi' ? 'आपका फ़ीडबैक Gurukul AI को बेहतर बनाने में मदद करता है।' : 'Your feedback helps us improve Gurukul AI.',
            style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: controller,
            maxLines: 4,
            decoration: InputDecoration(
              hintText: lang == 'hi' ? 'यहाँ लिखें…' : 'Write your feedback here…',
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              icon: const Icon(Icons.send),
              label: Text(lang == 'hi' ? 'भेजें' : 'Submit'),
              onPressed: () {
                Navigator.pop(ctx);
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(lang == 'hi' ? 'फ़ीडबैक के लिए धन्यवाद! 🙏' : 'Thanks for your feedback! 🙏'),
                    backgroundColor: AppTheme.primary,
                  ),
                );
              },
            ),
          ),
        ]),
      ),
    );
  }

  void _launchEmail() async {
    final uri = Uri.parse('mailto:rkprasada@gmail.com?subject=Gurukul AI Feedback');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  void _showHelpSheet(BuildContext context, String lang) {
    final faqs = lang == 'hi' ? [
      ('डायग्नोस्टिक टेस्ट क्या है?', 'यह एक मूल्यांकन है जो आपकी ताकत और कमज़ोरियों का विश्लेषण करता है।'),
      ('Dabbu कौन है?', 'Dabbu एक AI एजेंट है जो आपकी अध्ययन योजना और प्रगति का प्रबंधन करता है।'),
      ('NAGA कौन है?', 'NAGA आपका मानव मेंटर है जो Dabbu की योजनाओं की समीक्षा करता है।'),
      ('अभ्यास और मॉक टेस्ट में क्या अंतर है?', 'अभ्यास अनुकूली MCQ है। मॉक टेस्ट हर शनिवार का पूरा पेपर है।'),
    ] : [
      ('What is the Diagnostic Test?', 'An assessment that analyses your strengths and weak areas across your exam syllabus.'),
      ('Who is Dabbu?', 'Dabbu is the AI agent that manages your study plan, notes, and progress interventions.'),
      ('Who is NAGA?', 'NAGA is your human mentor who reviews and approves Dabbu\'s plans before you see them.'),
      ('Practice Test vs Mock Test?', 'Practice is adaptive MCQs anytime. Mock Test is the full Saturday paper with a timer.'),
    ];

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.6,
        maxChildSize: 0.9,
        builder: (_, sc) => ListView(
          controller: sc,
          padding: const EdgeInsets.fromLTRB(20, 24, 20, 24),
          children: [
            Text(
              lang == 'hi' ? 'सहायता और FAQ' : 'Help & FAQ',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 16),
            ...faqs.map((faq) => Card(
              margin: const EdgeInsets.only(bottom: 10),
              child: ExpansionTile(
                title: Text(faq.$1, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                    child: Text(faq.$2, style: TextStyle(color: Colors.grey.shade700)),
                  ),
                ],
              ),
            )),
            const SizedBox(height: 8),
            ListTile(
              leading: const Icon(Icons.mail_outline, color: Colors.orange),
              title: Text(lang == 'hi' ? 'और सहायता चाहिए?' : 'Need more help?'),
              subtitle: const Text('rkprasada@gmail.com'),
              onTap: () {
                Navigator.pop(ctx);
                launchUrl(Uri.parse('mailto:rkprasada@gmail.com'));
              },
            ),
          ],
        ),
      ),
    );
  }

  void _confirmLogout(BuildContext context, AuthProvider auth, String lang) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(lang == 'hi' ? 'लॉग आउट?' : 'Log Out?'),
        content: Text(lang == 'hi' ? 'क्या आप वाकई लॉग आउट करना चाहते हैं?' : 'Are you sure you want to log out?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(lang == 'hi' ? 'रद्द करें' : 'Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              Navigator.pop(context);
              auth.logout();
            },
            child: Text(lang == 'hi' ? 'लॉग आउट' : 'Log Out',
                style: const TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String label;
  const _SectionHeader({required this.label});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 6),
      child: Text(
        label.toUpperCase(),
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w800,
          color: Colors.grey.shade500,
          letterSpacing: 1.2,
        ),
      ),
    );
  }
}

class _Tile extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _Tile({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Container(
        width: 40, height: 40,
        decoration: BoxDecoration(
          color: color.withOpacity(0.12),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: color, size: 20),
      ),
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
      subtitle: Text(subtitle, style: const TextStyle(fontSize: 12)),
      trailing: const Icon(Icons.chevron_right, size: 18, color: Colors.grey),
      onTap: onTap,
    );
  }
}
