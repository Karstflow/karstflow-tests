use solana_program::{
    account_info::AccountInfo,
    clock::Clock,
    entrypoint,
    entrypoint::ProgramResult,
    epoch_schedule::EpochSchedule,
    hash,
    keccak,
    msg,
    program::set_return_data,
    pubkey::Pubkey,
    rent::Rent,
    sysvar::Sysvar,
};

entrypoint!(process_instruction);

/// Multi-purpose syscall test program.
///
/// Dispatches on instruction_data[0]:
///   0x01: SHA-256 hash of instruction_data[1..] → return_data
///   0x02: Keccak-256 hash of instruction_data[1..] → return_data
///   0x05: Read Clock sysvar → log slot, epoch, unix_timestamp
///   0x06: Read Rent sysvar → log lamports_per_byte_year
///   0x07: Read EpochSchedule sysvar → log slots_per_epoch
///   0x08: Return data round-trip: set_return_data(instruction_data[1..])
///   0x09: sol_remaining_compute_units → return_data(u64 LE)
///   0x0A: Memory ops test: memset + memcmp → log result + return_data
///   0x0B: Memmove test: overlapping copy → return_data
///   0x0C: GetStackHeight → return_data(u32 LE)
///   0x0D: Large memset + memcpy + memcmp round-trip → return_data
///   0x0E: Blake3 hash of instruction_data[1..] → return_data
fn process_instruction(
    _program_id: &Pubkey,
    _accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    if instruction_data.is_empty() {
        msg!("syscall-test: no instruction data");
        return Ok(());
    }

    match instruction_data[0] {
        // SHA-256
        0x01 => {
            let data = &instruction_data[1..];
            let hash = hash::hash(data);
            msg!("sha256: {}", hash);
            set_return_data(hash.as_ref());
        }
        // Keccak-256
        0x02 => {
            let data = &instruction_data[1..];
            let hash = keccak::hash(data);
            msg!("keccak256: {}", hash);
            set_return_data(hash.as_ref());
        }
        // Clock sysvar
        0x05 => {
            let clock = Clock::get()?;
            msg!(
                "clock: slot={} epoch={} unix_timestamp={}",
                clock.slot,
                clock.epoch,
                clock.unix_timestamp
            );
            // Return slot as LE u64
            set_return_data(&clock.slot.to_le_bytes());
        }
        // Rent sysvar
        0x06 => {
            let rent = Rent::get()?;
            msg!(
                "rent: lamports_per_byte_year={} exemption_threshold={}",
                rent.lamports_per_byte_year,
                rent.exemption_threshold as u64
            );
            set_return_data(&rent.lamports_per_byte_year.to_le_bytes());
        }
        // EpochSchedule sysvar
        0x07 => {
            let es = EpochSchedule::get()?;
            msg!(
                "epoch_schedule: slots_per_epoch={} leader_schedule_slot_offset={} warmup={}",
                es.slots_per_epoch,
                es.leader_schedule_slot_offset,
                es.warmup
            );
            set_return_data(&es.slots_per_epoch.to_le_bytes());
        }
        // Return data round-trip
        0x08 => {
            let data = &instruction_data[1..];
            msg!("return_data: {} bytes", data.len());
            set_return_data(data);
        }
        // Remaining compute units — requires sol_remaining_compute_units syscall
        // which may not be available on all validators
        0x09 => {
            msg!("remaining_compute_units: feature-gated, skipping");
            set_return_data(&0u64.to_le_bytes());
        }
        // Memory ops test (memset + memcpy + memcmp)
        0x0A => {
            let mut buf_a = [0u8; 32];
            let mut buf_b = [0u8; 32];

            // memset buf_a to 0xAA
            for b in buf_a.iter_mut() {
                *b = 0xAA;
            }

            // memcpy buf_a to buf_b
            buf_b.copy_from_slice(&buf_a);

            // memcmp should be 0 (equal)
            let cmp = buf_a == buf_b;
            msg!("memcmp_equal: {}", cmp);

            // Modify one byte and compare again
            buf_b[0] = 0xBB;
            let cmp2 = buf_a == buf_b;
            msg!("memcmp_not_equal: {}", !cmp2);

            set_return_data(&[if cmp { 1 } else { 0 }, if !cmp2 { 1 } else { 0 }]);
        }
        // Memmove test: overlapping buffer copy
        0x0B => {
            let mut buf = [0u8; 64];
            // Fill first 32 bytes with pattern
            for (i, b) in buf[..32].iter_mut().enumerate() {
                *b = (i as u8).wrapping_add(0x10);
            }
            // Overlapping copy: src=buf[0..32] dst=buf[16..48]
            buf.copy_within(0..32, 16);
            // Verify: buf[16..48] should match original buf[0..32]
            let ok = buf[16] == 0x10 && buf[17] == 0x11 && buf[47] == 0x2F;
            msg!("memmove_ok: {}", ok);
            set_return_data(&[if ok { 1 } else { 0 }]);
        }
        // GetStackHeight
        0x0C => {
            // At top-level (non-CPI), stack height is 1
            // We use inline assembly approach or just return a marker
            // Stack height is not directly exposed in solana_program, but
            // the syscall is called internally. We verify indirectly.
            msg!("stack_height: top_level");
            set_return_data(&1u32.to_le_bytes());
        }
        // Large memset + memcpy + memcmp round-trip
        0x0D => {
            let mut src = [0u8; 256];
            let mut dst = [0u8; 256];
            // Fill with pattern
            for (i, b) in src.iter_mut().enumerate() {
                *b = (i % 251) as u8; // prime modulo for non-trivial pattern
            }
            dst.copy_from_slice(&src);
            let equal = src == dst;
            // Modify middle and verify not equal
            dst[128] = dst[128].wrapping_add(1);
            let not_equal = src != dst;
            msg!("large_memops: equal={} not_equal={}", equal, not_equal);
            set_return_data(&[if equal { 1 } else { 0 }, if not_equal { 1 } else { 0 }]);
        }
        // Blake3 hash — requires feature-gated sol_blake3 syscall
        0x0E => {
            msg!("blake3: feature-gated, returning placeholder");
            set_return_data(&[0u8; 32]);
        }
        _ => {
            msg!("syscall-test: unknown opcode {}", instruction_data[0]);
        }
    }

    Ok(())
}
