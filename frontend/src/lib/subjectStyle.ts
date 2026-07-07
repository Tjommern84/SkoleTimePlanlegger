import {
  BookOpen,
  Sigma,
  Languages,
  Compass,
  Leaf,
  Globe2,
  Landmark,
  Dumbbell,
  MessagesSquare,
  Star,
  Music2,
  Palette,
  UtensilsCrossed,
  type LucideIcon,
} from "lucide-react";

interface SubjectStyle {
  bg: string;
  text: string;
  icon: LucideIcon;
}

// Muted pastels per subject, deliberately avoiding strong primary colors --
// text colors are hand-picked for AA contrast against their bg.
const SUBJECT_STYLES: Record<string, SubjectStyle> = {
  NO: { bg: "#DCEBF7", text: "#2B5D7E", icon: BookOpen },
  MA: { bg: "#E1EFE1", text: "#3C6E45", icon: Sigma },
  EN: { bg: "#EAE3F5", text: "#6647A0", icon: Languages },
  UV: { bg: "#E7E4DC", text: "#6F6656", icon: Compass },
  NAT: { bg: "#DFF3EA", text: "#2E7A5C", icon: Leaf },
  SAM: { bg: "#FBE7D4", text: "#9C5A20", icon: Globe2 },
  KRLE: { bg: "#F6EBD2", text: "#8A6A1F", icon: Landmark },
  KROV: { bg: "#D9EEF2", text: "#1E6E7D", icon: Dumbbell },
  SPRAK: { bg: "#F8DCE0", text: "#A14C5A", icon: MessagesSquare },
  VALG: { bg: "#D9EEEA", text: "#1F6F63", icon: Star },
  MUS: { bg: "#F3DCE6", text: "#9A4E68", icon: Music2 },
  KH: { bg: "#FCE3D2", text: "#A15A2E", icon: Palette },
  MH: { bg: "#EFDAC9", text: "#7A4A24", icon: UtensilsCrossed },
};

const FALLBACK: SubjectStyle = { bg: "#E7E4DC", text: "#6F6656", icon: BookOpen };

export function getSubjectStyle(shortCode: string): SubjectStyle {
  return SUBJECT_STYLES[shortCode] ?? FALLBACK;
}
