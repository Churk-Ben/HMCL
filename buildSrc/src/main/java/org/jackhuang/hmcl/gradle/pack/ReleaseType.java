/*
 * Hello Minecraft! Launcher
 * Copyright (C) 2026 huangyuhui <huanghongxun2008@126.com> and contributors
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */
package org.jackhuang.hmcl.gradle.pack;

/// Linux packaging metadata for one HMCL release type.
///
/// The package name, installed command, desktop file, and alternatives
/// priority are centralized here so [CreateDeb] and [CreateRpm] stay focused on
/// their respective archive layouts instead of duplicating channel branching.
public enum ReleaseType {
    STABLE("stable", "hmcl", "HMCL", 100),
    DEVELOPMENT("beta", "hmcl-beta", "HMCL (Beta)", 200),
    NIGHTLY("nightly", "hmcl-nightly", "HMCL (Nightly)", 300),
    EXPERIMENTAL("exp", "hmcl-exp", "HMCL (Experimental)", 400);

    private final String name;
    private final String packageName;
    private final String displayName;
    private final int alternativesPriority;

    ReleaseType(String name, String packageName, String displayName, int alternativesPriority) {
        this.name = name;
        this.packageName = packageName;
        this.displayName = displayName;
        this.alternativesPriority = alternativesPriority;
    }

    /// Channel identifier used in command names, for example `stable`.
    public String getName() {
        return name;
    }

    /// Package name used by the Debian and RPM packagers.
    public String getPackageName() {
        return packageName;
    }

    /// Human-readable name shown in desktop entries.
    public String getDisplayName() {
        return displayName;
    }

    /// Priority used when registering the generic `hmcl` alias.
    public int getAlternativesPriority() {
        return alternativesPriority;
    }
}
