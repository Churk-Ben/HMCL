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
package org.jackhuang.hmcl.gradle.utils;

import org.jetbrains.annotations.NotNullByDefault;
import org.jetbrains.annotations.Unmodifiable;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/// Helpers for computing message digests in build logic.
///
/// The standard digest factory throws a checked exception even though every
/// algorithm used here is guaranteed to be available, so these helpers wrap that
/// boilerplate and provide the hexadecimal formatting used by package metadata.
@NotNullByDefault
public final class DigestUtils {

    /// Prevents instantiation of this utility class.
    private DigestUtils() {
    }

    /// Creates a message digest, wrapping the checked exception that cannot occur.
    ///
    /// The returned instance is stateful and may be fed incrementally with
    /// `MessageDigest#update` for streaming inputs.
    ///
    /// @param algorithm the standard digest algorithm name, for example `SHA-256`
    /// @return a new message digest
    public static MessageDigest newDigest(String algorithm) {
        try {
            return MessageDigest.getInstance(algorithm);
        } catch (NoSuchAlgorithmException e) {
            throw new AssertionError("Unsupported digest algorithm: " + algorithm, e);
        }
    }

    /// Computes the digest of `data`.
    ///
    /// @param algorithm the standard digest algorithm name
    /// @param data      the bytes to hash
    /// @return the raw digest bytes
    public static byte @Unmodifiable [] digest(String algorithm, byte @Unmodifiable [] data) {
        return newDigest(algorithm).digest(data);
    }

    /// Computes the digest of the concatenation of `first` and `second`.
    ///
    /// The inputs are fed incrementally so they are never copied into a single
    /// buffer, which matters when one of them is a multi-megabyte payload.
    ///
    /// @param algorithm the standard digest algorithm name
    /// @param first     the first input
    /// @param second    the second input
    /// @return the raw digest bytes
    public static byte @Unmodifiable [] digest(String algorithm,
                                               byte @Unmodifiable [] first,
                                               byte @Unmodifiable [] second) {
        MessageDigest digest = newDigest(algorithm);
        digest.update(first);
        digest.update(second);
        return digest.digest();
    }

    /// Computes the digest of `data` and formats it as lowercase hexadecimal.
    ///
    /// @param algorithm the standard digest algorithm name
    /// @param data      the bytes to hash
    /// @return the lowercase hexadecimal digest
    public static String hexDigest(String algorithm, byte @Unmodifiable [] data) {
        return toHex(digest(algorithm, data));
    }

    /// Formats bytes as lowercase hexadecimal.
    ///
    /// @param bytes the bytes to format
    /// @return the lowercase hexadecimal string
    public static String toHex(byte @Unmodifiable [] bytes) {
        return HexFormat.of().formatHex(bytes);
    }
}
