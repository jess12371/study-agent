// Halaman signup — email, nama, password + konfirmasi, lalu verifikasi OTP.
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { GraduationCap, Loader2, MailCheck } from "lucide-react";
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

type SignupValues = {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
};

export default function SignupPage() {
  const router = useRouter();
  const { setAuth, isAuthenticated, isHydrated } = useAuth();
  const { t } = useLanguage();
  const [submitting, setSubmitting] = useState(false);
  const [step, setStep] = useState<"form" | "otp">("form");
  const [pendingEmail, setPendingEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [verifying, setVerifying] = useState(false);

  const signupSchema = useMemo(
    () =>
      z
        .object({
          name: z.string().min(1, t("validationName")).max(100),
          email: z.string().email(t("validationEmail")),
          password: z
            .string()
            .min(8, t("validationPasswordMin"))
            .regex(/[A-Z]/, t("validationPasswordUpper"))
            .regex(/\d/, t("validationPasswordNumber")),
          confirmPassword: z.string(),
        })
        .refine((data) => data.password === data.confirmPassword, {
          message: t("validationPasswordMatch"),
          path: ["confirmPassword"],
        }),
    [t]
  );

  const form = useForm<SignupValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: { name: "", email: "", password: "", confirmPassword: "" },
  });

  useEffect(() => {
    if (isHydrated && isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isHydrated, isAuthenticated, router]);

  const onSubmit = async (values: SignupValues) => {
    setSubmitting(true);
    try {
      await authApi.signup({
        name: values.name,
        email: values.email,
        password: values.password,
      });
      setPendingEmail(values.email);
      setStep("otp");
      toast.info(t("otpInfoMock"));
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerify = async () => {
    if (!/^\d{6}$/.test(otp)) {
      toast.error(t("otpInvalid"));
      return;
    }
    setVerifying(true);
    try {
      const data = await authApi.verifyOtp(pendingEmail, otp);
      setAuth(data.access_token, data.user);
      toast.success(t("emailVerified"));
      router.push("/dashboard");
    } catch (error) {
      toast.error(getErrorMessage(error));
    } finally {
      setVerifying(false);
    }
  };

  const handleResend = async () => {
    try {
      await authApi.resendOtp(pendingEmail);
      toast.success(t("otpResent"));
    } catch (error) {
      toast.error(getErrorMessage(error));
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/30 px-4 py-12">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-2 text-center">
          <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-lg bg-primary/10">
            {step === "form" ? (
              <GraduationCap className="h-6 w-6 text-primary" />
            ) : (
              <MailCheck className="h-6 w-6 text-primary" />
            )}
          </div>
          <CardTitle>
            {step === "form" ? t("signupTitle") : t("otpTitle")}
          </CardTitle>
          <CardDescription>
            {step === "form"
              ? t("signupDesc")
              : t("otpDesc", { email: pendingEmail })}
          </CardDescription>
        </CardHeader>

        <CardContent>
          {step === "form" ? (
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("name")}</FormLabel>
                      <FormControl>
                        <Input
                          placeholder={t("namePlaceholder")}
                          autoComplete="name"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
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
                          placeholder={t("passwordHint")}
                          autoComplete="new-password"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="confirmPassword"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t("confirmPassword")}</FormLabel>
                      <FormControl>
                        <Input
                          type="password"
                          placeholder={t("confirmPlaceholder")}
                          autoComplete="new-password"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <Button type="submit" className="w-full" disabled={submitting}>
                  {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  {t("signupButton")}
                </Button>
              </form>
            </Form>
          ) : (
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium" htmlFor="otp">
                  {t("otpLabel")}
                </label>
                <Input
                  id="otp"
                  inputMode="numeric"
                  maxLength={6}
                  placeholder={t("otpPlaceholder")}
                  value={otp}
                  onChange={(event) =>
                    setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))
                  }
                />
              </div>
              <Button
                onClick={handleVerify}
                className="w-full"
                disabled={verifying || otp.length !== 6}
              >
                {verifying && <Loader2 className="h-4 w-4 animate-spin" />}
                {t("verifyContinue")}
              </Button>
              <div className="flex justify-between text-sm">
                <button
                  type="button"
                  onClick={handleResend}
                  className="font-medium text-primary hover:underline"
                >
                  {t("resendCode")}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setStep("form");
                    setOtp("");
                  }}
                  className="text-muted-foreground hover:underline"
                >
                  {t("back")}
                </button>
              </div>
            </div>
          )}
        </CardContent>

        <CardFooter className="justify-center text-sm text-muted-foreground">
          {t("haveAccount")}&nbsp;
          <Link href="/login" className="font-medium text-primary hover:underline">
            {t("loginLink")}
          </Link>
        </CardFooter>
      </Card>
    </div>
  );
}
