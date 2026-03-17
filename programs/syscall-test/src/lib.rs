use solana_program::{
    account_info::AccountInfo,
    clock::Clock,
    entrypoint,
    entrypoint::ProgramResult,
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
///   0x08: Return data round-trip: set_return_data(instruction_data[1..])
///   0x0A: Memory ops test: memset + memcmp → log result + return_data
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
        // Return data round-trip
        0x08 => {
            let data = &instruction_data[1..];
            msg!("return_data: {} bytes", data.len());
            set_return_data(data);
        }
        // Memory ops test
        0x0A => {
            let mut buf_a = [0u8; 32];
            let mut buf_b = [0u8; 32];

            // memset buf_a to 0xAA
            // Using a loop since sol_memset_ is not directly exposed
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
        _ => {
            msg!("syscall-test: unknown opcode {}", instruction_data[0]);
        }
    }

    Ok(())
}
