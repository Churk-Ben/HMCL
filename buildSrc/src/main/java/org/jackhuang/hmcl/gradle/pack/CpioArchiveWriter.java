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

import org.jetbrains.annotations.NotNullByDefault;
import org.jetbrains.annotations.Unmodifiable;

import java.io.Closeable;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

/// Writes an SVR4 `newc` cpio archive, the payload format expected by RPM packages.
///
/// Each entry is stored with an ASCII header (`070701` magic followed by thirteen
/// eight-digit hexadecimal fields), a NUL-terminated name and the file content.
/// The name and the content are each padded with NUL bytes so the following
/// header starts on a four-byte boundary; because the fixed header is not a
/// multiple of four, the name padding is computed from the combined length of the
/// header and the name.
///
/// The writer counts the number of uncompressed bytes it emits so the caller can
/// record the archive size in the RPM signature and header without buffering a
/// second copy of the payload.
@NotNullByDefault
public final class CpioArchiveWriter implements Closeable {

    /// ASCII magic identifying an SVR4 `newc` archive without CRC.
    private static final String MAGIC = "070701";

    /// Size in bytes of the fixed ASCII header preceding every entry name.
    private static final int HEADER_SIZE = 110;

    /// Name of the synthetic last entry that terminates a cpio archive.
    private static final String TRAILER_NAME = "TRAILER!!!";

    /// Underlying stream receiving the archive bytes.
    private final OutputStream out;

    /// Number of uncompressed bytes written so far, including header padding.
    private long bytesWritten;

    /// Inode number assigned to the next entry.
    private int nextInode = 1;

    /// Whether the trailer has already been written.
    private boolean finished;

    /// Creates a writer emitting the archive into `out`.
    ///
    /// @param out the destination stream; it is closed when this writer is closed
    public CpioArchiveWriter(OutputStream out) {
        this.out = out;
    }

    /// Appends one file, directory or symbolic link entry.
    ///
    /// The `path` is stored relative to the archive root with a leading `./`, as
    /// produced by `rpmbuild`. A single trailing slash is tolerated and removed
    /// because RPM records directory basenames without it.
    ///
    /// @param path    absolute installed path, for example `/usr/bin/hmcl`
    /// @param mode    full Unix mode including the file-type bits
    /// @param content file content; empty for directories
    /// @param mtime   modification time in seconds since the Unix epoch
    /// @throws IOException if writing to the underlying stream fails
    public void putEntry(String path, int mode, byte @Unmodifiable [] content, long mtime) throws IOException {
        if (finished)
            throw new IllegalStateException("Cpio archive already finished");

        String name = toArchiveName(path);
        byte[] nameBytes = (name + "\0").getBytes(StandardCharsets.UTF_8);

        StringBuilder header = new StringBuilder(HEADER_SIZE);
        header.append(MAGIC);
        appendField(header, nextInode++);
        appendField(header, mode);
        appendField(header, 0);                 // uid
        appendField(header, 0);                 // gid
        appendField(header, 1);                 // nlink
        appendField(header, mtime);
        appendField(header, content.length);    // filesize
        appendField(header, 0);                 // device major
        appendField(header, 0);                 // device minor
        appendField(header, 0);                 // rdev major
        appendField(header, 0);                 // rdev minor
        appendField(header, nameBytes.length);  // namesize, including the NUL
        appendField(header, 0);                 // check, unused by newc

        write(header.toString().getBytes(StandardCharsets.US_ASCII));
        write(nameBytes);
        writeZeros((4 - ((HEADER_SIZE + nameBytes.length) % 4)) % 4);
        write(content);
        writeZeros((4 - (content.length % 4)) % 4);
    }

    /// Writes the archive terminator.
    ///
    /// This method is idempotent to keep [#close()] safe when the caller already
    /// finished the archive explicitly.
    ///
    /// @throws IOException if writing to the underlying stream fails
    public void finish() throws IOException {
        if (finished)
            return;

        String name = TRAILER_NAME;
        byte[] nameBytes = (name + "\0").getBytes(StandardCharsets.UTF_8);

        StringBuilder header = new StringBuilder(HEADER_SIZE);
        header.append(MAGIC);
        appendField(header, 0);                 // inode
        appendField(header, 0);                 // mode
        appendField(header, 0);                 // uid
        appendField(header, 0);                 // gid
        appendField(header, 1);                 // nlink
        appendField(header, 0);                 // mtime
        appendField(header, 0);                 // filesize
        appendField(header, 0);                 // device major
        appendField(header, 0);                 // device minor
        appendField(header, 0);                 // rdev major
        appendField(header, 0);                 // rdev minor
        appendField(header, nameBytes.length);  // namesize, including the NUL
        appendField(header, 0);                 // check, unused by newc

        write(header.toString().getBytes(StandardCharsets.US_ASCII));
        write(nameBytes);
        writeZeros((4 - ((HEADER_SIZE + nameBytes.length) % 4)) % 4);
        finished = true;
    }

    /// Returns the number of uncompressed archive bytes written so far.
    ///
    /// @return the byte count of the archive without compression
    public long getBytesWritten() {
        return bytesWritten;
    }

    /// Finishes the archive if needed and closes the underlying stream.
    ///
    /// @throws IOException if finishing or closing fails
    @Override
    public void close() throws IOException {
        finish();
        out.close();
    }

    /// Converts an absolute install path into the `./`-prefixed archive name.
    private static String toArchiveName(String path) {
        String normalized = path.endsWith("/") ? path.substring(0, path.length() - 1) : path;
        return normalized.startsWith("/") ? "." + normalized : "./" + normalized;
    }

    /// Appends one zero-padded eight-digit hexadecimal field.
    private static void appendField(StringBuilder builder, long value) {
        String hex = Long.toHexString(value & 0xffffffffL);
        for (int i = hex.length(); i < 8; i++)
            builder.append('0');
        builder.append(hex);
    }

    /// Writes `count` NUL bytes, used for alignment padding.
    private void writeZeros(int count) throws IOException {
        for (int i = 0; i < count; i++)
            write(new byte[]{0});
    }

    /// Writes `bytes` and updates the running byte count.
    private void write(byte @Unmodifiable [] bytes) throws IOException {
        out.write(bytes);
        bytesWritten += bytes.length;
    }
}
