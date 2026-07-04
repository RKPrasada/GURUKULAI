import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/auth_provider.dart';
import '../theme/app_theme.dart';
import '../utils/constants.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  String _selectedExam = 'rrb_ntpc';
  String _selectedLang = 'en';

  void _showDemoDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusLarge)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Start Demo', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            const Text('Choose your exam and preferred language'),
            const SizedBox(height: 24),
            const Text('Select Exam', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 8),
            ...List.generate(AppConstants.examKeys.length, (i) => RadioListTile<String>(
              value: AppConstants.examKeys[i],
              groupValue: _selectedExam,
              title: Text(AppConstants.supportedExams[i]),
              subtitle: Text(AppConstants.examDescriptions[i], style: const TextStyle(fontSize: 12)),
              onChanged: (v) => setState(() => _selectedExam = v!),
              activeColor: AppTheme.primary,
            )),
            const Divider(),
            const Text('Language', style: TextStyle(fontWeight: FontWeight.w600)),
            Row(
              children: [
                Expanded(child: RadioListTile<String>(
                  value: 'en', groupValue: _selectedLang, title: const Text('English'),
                  onChanged: (v) => setState(() => _selectedLang = v!),
                  activeColor: AppTheme.primary,
                )),
                Expanded(child: RadioListTile<String>(
                  value: 'hi', groupValue: _selectedLang, title: const Text('हिंदी'),
                  onChanged: (v) => setState(() => _selectedLang = v!),
                  activeColor: AppTheme.primary,
                )),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: () {
                  Navigator.pop(ctx);
                  context.read<AuthProvider>().demoLogin(_selectedExam, _selectedLang);
                },
                child: const Text('🚀 Start Demo'),
              ),
            ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [Color(0xFF5C35CC), Color(0xFF9C27B0)],
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Spacer(),
                const Text('📚', style: TextStyle(fontSize: 72)),
                const SizedBox(height: 16),
                const Text(
                  'VidyaBot',
                  style: TextStyle(color: Colors.white, fontSize: 42, fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Personalized AI Tutor\nfor Indian Competitive Exams',
                  style: TextStyle(color: Colors.white70, fontSize: 18, height: 1.4),
                ),
                const SizedBox(height: 12),
                const Text(
                  'RRB NTPC · NDA · JEE · NEET',
                  style: TextStyle(color: Colors.white54, fontSize: 14, letterSpacing: 1.5),
                ),
                const SizedBox(height: 8),
                const Text(
                  'बिना कोचिंग के अपनी परीक्षा की तैयारी करें',
                  style: TextStyle(color: Colors.white38, fontSize: 13),
                ),
                const Spacer(),
                if (auth.error != null)
                  Container(
                    padding: const EdgeInsets.all(12),
                    margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(
                      color: Colors.red.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
                    ),
                    child: Text(auth.error!, style: const TextStyle(color: Colors.white)),
                  ),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    onPressed: auth.isLoading ? null : _showDemoDialog,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: const BorderSide(color: Colors.white70),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
                      ),
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                    child: auth.isLoading
                        ? const SizedBox(height: 20, width: 20,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : const Text('🎭 Try Demo Mode', style: TextStyle(fontSize: 16)),
                  ),
                ),
                const SizedBox(height: 12),
                const Center(
                  child: Text(
                    'Google OAuth available when credentials are configured',
                    style: TextStyle(color: Colors.white38, fontSize: 11),
                    textAlign: TextAlign.center,
                  ),
                ),
                const SizedBox(height: 16),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
