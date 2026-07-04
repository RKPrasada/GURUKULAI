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

  void _showLoginSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusLarge)),
      ),
      builder: (ctx) => _LoginSheet(),
    );
  }

  void _showRegisterSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusLarge)),
      ),
      builder: (ctx) => _RegisterSheet(),
    );
  }

  void _showDemoDialog() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(AppTheme.radiusLarge)),
      ),
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setModalState) => Padding(
          padding: EdgeInsets.only(
            left: 24, right: 24, top: 24,
            bottom: MediaQuery.of(ctx).viewInsets.bottom + 24,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Try Demo Mode', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              const Text('No account needed — explore all features', style: TextStyle(color: Colors.grey)),
              const SizedBox(height: 20),
              const Text('Select Exam', style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              ...List.generate(AppConstants.examKeys.length, (i) => RadioListTile<String>(
                dense: true,
                value: AppConstants.examKeys[i],
                groupValue: _selectedExam,
                title: Text(AppConstants.supportedExams[i]),
                subtitle: Text(AppConstants.examDescriptions[i], style: const TextStyle(fontSize: 11)),
                onChanged: (v) { setState(() => _selectedExam = v!); setModalState(() {}); },
                activeColor: AppTheme.primary,
              )),
              const Divider(),
              const Text('Language', style: TextStyle(fontWeight: FontWeight.w600)),
              Row(
                children: [
                  Expanded(child: RadioListTile<String>(
                    dense: true,
                    value: 'en', groupValue: _selectedLang, title: const Text('English'),
                    onChanged: (v) { setState(() => _selectedLang = v!); setModalState(() {}); },
                    activeColor: AppTheme.primary,
                  )),
                  Expanded(child: RadioListTile<String>(
                    dense: true,
                    value: 'hi', groupValue: _selectedLang, title: const Text('हिंदी'),
                    onChanged: (v) { setState(() => _selectedLang = v!); setModalState(() {}); },
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
                  child: const Text('Start Demo'),
                ),
              ),
              const SizedBox(height: 8),
            ],
          ),
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
                const Text('🎓', style: TextStyle(fontSize: 72)),
                const SizedBox(height: 16),
                const Text(
                  'Gurukul AI',
                  style: TextStyle(color: Colors.white, fontSize: 42, fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Personalized AI Tutor\nfor Indian Competitive Exams',
                  style: TextStyle(color: Colors.white70, fontSize: 18, height: 1.4),
                ),
                const SizedBox(height: 12),
                const Text(
                  'RRB NTPC · ALP · Group D · NDA · JEE · NEET',
                  style: TextStyle(color: Colors.white54, fontSize: 13, letterSpacing: 1.2),
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
                  child: ElevatedButton(
                    onPressed: auth.isLoading ? null : _showLoginSheet,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: AppTheme.primary,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
                      ),
                    ),
                    child: auth.isLoading
                        ? const SizedBox(height: 20, width: 20,
                            child: CircularProgressIndicator(strokeWidth: 2))
                        : const Text('Login', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                  ),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton(
                    onPressed: auth.isLoading ? null : _showRegisterSheet,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: Colors.white,
                      side: const BorderSide(color: Colors.white70),
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(AppTheme.radiusMedium),
                      ),
                    ),
                    child: const Text('Create Account', style: TextStyle(fontSize: 16)),
                  ),
                ),
                const SizedBox(height: 12),
                Center(
                  child: TextButton(
                    onPressed: auth.isLoading ? null : _showDemoDialog,
                    child: const Text('Try Demo Mode', style: TextStyle(color: Colors.white54, fontSize: 13)),
                  ),
                ),
                const SizedBox(height: 8),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ── Login Sheet ────────────────────────────────────────────────────────────────

class _LoginSheet extends StatefulWidget {
  @override
  State<_LoginSheet> createState() => _LoginSheetState();
}

class _LoginSheetState extends State<_LoginSheet> {
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _obscure = true;
  final _formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _usernameCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    Navigator.pop(context);
    await context.read<AuthProvider>().login(_usernameCtrl.text.trim(), _passwordCtrl.text);
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    return Padding(
      padding: EdgeInsets.only(
        left: 24, right: 24, top: 24,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Login', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            const Text('Welcome back!', style: TextStyle(color: Colors.grey)),
            const SizedBox(height: 20),
            TextFormField(
              controller: _usernameCtrl,
              decoration: const InputDecoration(labelText: 'Username', prefixIcon: Icon(Icons.person_outline)),
              textInputAction: TextInputAction.next,
              validator: (v) => (v == null || v.trim().isEmpty) ? 'Enter username' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _passwordCtrl,
              obscureText: _obscure,
              decoration: InputDecoration(
                labelText: 'Password',
                prefixIcon: const Icon(Icons.lock_outline),
                suffixIcon: IconButton(
                  icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                  onPressed: () => setState(() => _obscure = !_obscure),
                ),
              ),
              textInputAction: TextInputAction.done,
              onFieldSubmitted: (_) => _submit(),
              validator: (v) => (v == null || v.isEmpty) ? 'Enter password' : null,
            ),
            if (auth.error != null) ...[
              const SizedBox(height: 8),
              Text(auth.error!, style: const TextStyle(color: Colors.red, fontSize: 13)),
            ],
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: auth.isLoading ? null : _submit,
                child: auth.isLoading
                    ? const SizedBox(height: 20, width: 20,
                        child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                    : const Text('Login', style: TextStyle(fontSize: 16)),
              ),
            ),
            const SizedBox(height: 8),
            const Center(
              child: Text(
                'NAGA mentor login: username = naga',
                style: TextStyle(color: Colors.grey, fontSize: 11),
              ),
            ),
            const SizedBox(height: 4),
          ],
        ),
      ),
    );
  }
}

// ── Register Sheet ─────────────────────────────────────────────────────────────

class _RegisterSheet extends StatefulWidget {
  @override
  State<_RegisterSheet> createState() => _RegisterSheetState();
}

class _RegisterSheetState extends State<_RegisterSheet> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _usernameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  String _exam = 'rrb_ntpc';
  String _lang = 'en';
  String? _trade;
  String? _discipline;
  bool _obscure = true;
  bool _obscure2 = true;

  @override
  void dispose() {
    _nameCtrl.dispose();
    _usernameCtrl.dispose();
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

  bool get _needsTrade => AppConstants.examsRequiringTrade.contains(_exam);
  bool get _needsDiscipline => AppConstants.examsRequiringDiscipline.contains(_exam);

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_needsTrade && (_trade == null || _trade!.isEmpty)) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please select your ITI trade')));
      return;
    }
    if (_needsDiscipline && (_discipline == null || _discipline!.isEmpty)) {
      ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please select your engineering discipline')));
      return;
    }
    Navigator.pop(context);
    await context.read<AuthProvider>().register(
      username: _usernameCtrl.text.trim(),
      email: _emailCtrl.text.trim(),
      password: _passwordCtrl.text,
      confirmPassword: _confirmCtrl.text,
      fullName: _nameCtrl.text.trim(),
      examTarget: _exam,
      language: _lang,
      trade: _needsTrade ? (_trade ?? '') : '',
      engineeringDiscipline: _needsDiscipline ? (_discipline ?? '') : '',
    );
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    return Padding(
      padding: EdgeInsets.only(
        left: 24, right: 24, top: 24,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Create Account', style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              const Text('Start your exam prep journey', style: TextStyle(color: Colors.grey)),
              const SizedBox(height: 20),
              TextFormField(
                controller: _nameCtrl,
                decoration: const InputDecoration(labelText: 'Full Name', prefixIcon: Icon(Icons.badge_outlined)),
                textInputAction: TextInputAction.next,
                validator: (v) => (v == null || v.trim().length < 2) ? 'Enter your full name' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _usernameCtrl,
                decoration: const InputDecoration(labelText: 'Username', prefixIcon: Icon(Icons.person_outline)),
                textInputAction: TextInputAction.next,
                validator: (v) => (v == null || v.trim().length < 3) ? 'Min 3 characters' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _emailCtrl,
                keyboardType: TextInputType.emailAddress,
                decoration: const InputDecoration(labelText: 'Email', prefixIcon: Icon(Icons.email_outlined)),
                textInputAction: TextInputAction.next,
                validator: (v) => (v == null || !v.contains('@')) ? 'Enter valid email' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _passwordCtrl,
                obscureText: _obscure,
                decoration: InputDecoration(
                  labelText: 'Password (min 8 chars)',
                  prefixIcon: const Icon(Icons.lock_outline),
                  suffixIcon: IconButton(
                    icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                    onPressed: () => setState(() => _obscure = !_obscure),
                  ),
                ),
                textInputAction: TextInputAction.next,
                validator: (v) => (v == null || v.length < 8) ? 'Minimum 8 characters' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _confirmCtrl,
                obscureText: _obscure2,
                decoration: InputDecoration(
                  labelText: 'Confirm Password',
                  prefixIcon: const Icon(Icons.lock_outline),
                  suffixIcon: IconButton(
                    icon: Icon(_obscure2 ? Icons.visibility_outlined : Icons.visibility_off_outlined),
                    onPressed: () => setState(() => _obscure2 = !_obscure2),
                  ),
                ),
                textInputAction: TextInputAction.done,
                validator: (v) => v != _passwordCtrl.text ? 'Passwords do not match' : null,
              ),
              const SizedBox(height: 16),
              const Text('Target Exam', style: TextStyle(fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              DropdownButtonFormField<String>(
                value: _exam,
                decoration: const InputDecoration(prefixIcon: Icon(Icons.school_outlined)),
                items: List.generate(AppConstants.examKeys.length, (i) => DropdownMenuItem(
                  value: AppConstants.examKeys[i],
                  child: Text('${AppConstants.supportedExams[i]}  —  ${AppConstants.examDescriptions[i]}',
                      style: const TextStyle(fontSize: 13)),
                )),
                onChanged: (v) => setState(() {
                  _exam = v!;
                  _trade = null;
                  _discipline = null;
                }),
              ),
              if (_needsTrade) ...[
                const SizedBox(height: 12),
                const Text('ITI Trade', style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: _trade,
                  hint: const Text('Select your trade'),
                  decoration: const InputDecoration(prefixIcon: Icon(Icons.build_outlined)),
                  items: AppConstants.itiTrades.map((t) => DropdownMenuItem(value: t, child: Text(t))).toList(),
                  onChanged: (v) => setState(() => _trade = v),
                ),
              ],
              if (_needsDiscipline) ...[
                const SizedBox(height: 12),
                const Text('Engineering Discipline', style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: _discipline,
                  hint: const Text('Select discipline'),
                  decoration: const InputDecoration(prefixIcon: Icon(Icons.engineering_outlined)),
                  items: AppConstants.engineeringDisciplines
                      .map((d) => DropdownMenuItem(value: d, child: Text(d)))
                      .toList(),
                  onChanged: (v) => setState(() => _discipline = v),
                ),
              ],
              const SizedBox(height: 12),
              Row(
                children: [
                  const Text('Language: ', style: TextStyle(fontWeight: FontWeight.w600)),
                  const SizedBox(width: 8),
                  ChoiceChip(
                    label: const Text('English'),
                    selected: _lang == 'en',
                    onSelected: (_) => setState(() => _lang = 'en'),
                  ),
                  const SizedBox(width: 8),
                  ChoiceChip(
                    label: const Text('हिंदी'),
                    selected: _lang == 'hi',
                    onSelected: (_) => setState(() => _lang = 'hi'),
                  ),
                ],
              ),
              if (auth.error != null) ...[
                const SizedBox(height: 8),
                Text(auth.error!, style: const TextStyle(color: Colors.red, fontSize: 13)),
              ],
              const SizedBox(height: 20),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: auth.isLoading ? null : _submit,
                  child: auth.isLoading
                      ? const SizedBox(height: 20, width: 20,
                          child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                      : const Text('Create Account', style: TextStyle(fontSize: 16)),
                ),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
}
