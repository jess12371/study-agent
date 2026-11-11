// Halaman login — form email + password.
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { GraduationCap, Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { authApi, getErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/hooks/use-auth";
import { useLanguage } from "@/lib/language-context";

type LoginValues = { email: string; password: string };

export default function LoginPage() {
  const router = useRouter();
  const { setAuth, isAuthenticated, isHydrated } = useAuth();
  const { t } = useLanguage();
  const [submitting, setSubmitting] = useState(false);

  const loginSchema = useMemo(
    () =>
      z.object({
        email: z.string().email(t("validationEmail")),
        password: z.string().min(1, t("validationPasswordRequired")),
      }),
    [t]
  );

  const form = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  // Kalau sudah login, langsung ke dashboard.
  useEffect(() => {
    if (isHydrated && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isHydrated, isAuthenticated, router]);

  const onSubmit = async (values: LoginValues) => {
    setSubmitting(true);
    try {
      const data = await authApi.login(values);
      setAuth(data.access_token, data.user);
      toast.success(t("loginSuccess"));
      router.push("/dashboard");
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4 py-12">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-2 text-center">
          <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10">
            <GraduationCap className="h-6 w-6 text-primary" />
          </div>
          <CardTitle>{t("loginTitle")}</CardTitle>
          <CardDescription>{t("loginSubtitle")}</CardDescription>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("email")}</FormLabel>
                    <FormControl>
                      <Input
                        type="email"
                        placeholder={t("emailPlaceholder")}
                        autoComplete="email"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>{t("password")}</FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        placeholder={t("passwordPlaceholder")}
                        autoComplete="current-password"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                {t("loginButton")}
              </Button>
            </form>
          </Form>
        </CardContent>
        <CardFooter className="justify-center text-sm text-muted-foreground">
          {t("noAccount")}&nbsp;
          <Link href="/signup" className="font-medium text-primary hover:underline">
            {t("signupLink")}
          </Link>
        </CardFooter>
      </Card>
    </div>
  );
}
