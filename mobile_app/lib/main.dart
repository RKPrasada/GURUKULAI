import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:provider/provider.dart';

import 'providers/auth_provider.dart';
import 'providers/session_provider.dart';
import 'screens/onboarding_screen.dart';
import 'screens/home_screen.dart';
import 'theme/app_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env');
  runApp(const GurkulAIApp());
}

class GurkulAIApp extends StatelessWidget {
  const GurkulAIApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider()..loadSavedSession()),
        ChangeNotifierProvider(create: (_) => SessionProvider()),
      ],
      child: MaterialApp(
        title: 'Gurukul AI',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light(),
        home: const _WarmUpOnStart(),
      ),
    );
  }
}

// Fires a /health ping as soon as the app opens so Cloud Run isn't cold
// when the user presses Login.
class _WarmUpOnStart extends StatefulWidget {
  const _WarmUpOnStart();

  @override
  State<_WarmUpOnStart> createState() => _WarmUpOnStartState();
}

class _WarmUpOnStartState extends State<_WarmUpOnStart> {
  @override
  void initState() {
    super.initState();
    // Kick off warm-up without blocking the UI
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<AuthProvider>().warmUp();
    });
  }

  @override
  Widget build(BuildContext context) {
    return const _AppEntry();
  }
}

class _AppEntry extends StatelessWidget {
  const _AppEntry();

  @override
  Widget build(BuildContext context) {
    return Consumer<AuthProvider>(
      builder: (context, auth, _) {
        if (auth.isLoading) {
          return const Scaffold(
            body: Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircularProgressIndicator(),
                  SizedBox(height: 16),
                  Text('Loading Gurukul AI...'),
                ],
              ),
            ),
          );
        }
        return auth.isAuthenticated ? const HomeScreen() : const OnboardingScreen();
      },
    );
  }
}
