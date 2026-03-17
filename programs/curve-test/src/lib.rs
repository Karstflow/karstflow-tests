use solana_program::{
    account_info::AccountInfo,
    entrypoint,
    entrypoint::ProgramResult,
    msg,
    program::set_return_data,
    pubkey::Pubkey,
};

entrypoint!(process_instruction);

// alt_bn128 syscall group operations
const ALT_BN128_ADD: u64 = 0;
const ALT_BN128_MUL: u64 = 1;

extern "C" {
    fn sol_alt_bn128_group_op(
        group_op: u64,
        input: *const u8,
        input_size: u64,
        result: *mut u8,
    ) -> u64;
}

/// Curve operations test program.
///
/// Dispatches on instruction_data[0]:
///   0x01: alt_bn128 point addition (128 bytes input → 64 bytes output)
///   0x02: alt_bn128 scalar multiplication (96 bytes input → 64 bytes output)
///   0x03: alt_bn128 identity — add point + zero → same point
fn process_instruction(
    _program_id: &Pubkey,
    _accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    if instruction_data.is_empty() {
        msg!("curve-test: no instruction data");
        return Ok(());
    }

    match instruction_data[0] {
        // alt_bn128 addition
        0x01 => {
            let input = &instruction_data[1..];
            if input.len() < 128 {
                msg!("alt_bn128_add: need 128 bytes, got {}", input.len());
                return Err(
                    solana_program::program_error::ProgramError::InvalidInstructionData,
                );
            }
            let mut result = [0u8; 64];
            let rc = unsafe {
                sol_alt_bn128_group_op(
                    ALT_BN128_ADD,
                    input.as_ptr(),
                    128,
                    result.as_mut_ptr(),
                )
            };
            if rc != 0 {
                msg!("alt_bn128_add: syscall error {}", rc);
                return Err(
                    solana_program::program_error::ProgramError::InvalidArgument,
                );
            }
            msg!("alt_bn128_add: success");
            set_return_data(&result);
        }
        // alt_bn128 scalar multiplication
        0x02 => {
            let input = &instruction_data[1..];
            if input.len() < 96 {
                msg!("alt_bn128_mul: need 96 bytes, got {}", input.len());
                return Err(
                    solana_program::program_error::ProgramError::InvalidInstructionData,
                );
            }
            let mut result = [0u8; 64];
            let rc = unsafe {
                sol_alt_bn128_group_op(
                    ALT_BN128_MUL,
                    input.as_ptr(),
                    96,
                    result.as_mut_ptr(),
                )
            };
            if rc != 0 {
                msg!("alt_bn128_mul: syscall error {}", rc);
                return Err(
                    solana_program::program_error::ProgramError::InvalidArgument,
                );
            }
            msg!("alt_bn128_mul: success");
            set_return_data(&result);
        }
        // alt_bn128 identity: point + zero = point
        0x03 => {
            let input = &instruction_data[1..];
            if input.len() < 64 {
                msg!(
                    "alt_bn128_identity: need 64 bytes, got {}",
                    input.len()
                );
                return Err(
                    solana_program::program_error::ProgramError::InvalidInstructionData,
                );
            }
            let mut add_input = [0u8; 128];
            add_input[..64].copy_from_slice(&input[..64]);
            // Second 64 bytes remain zero (point at infinity)
            let mut result = [0u8; 64];
            let rc = unsafe {
                sol_alt_bn128_group_op(
                    ALT_BN128_ADD,
                    add_input.as_ptr(),
                    128,
                    result.as_mut_ptr(),
                )
            };
            if rc != 0 {
                msg!("alt_bn128_identity: syscall error {}", rc);
                return Err(
                    solana_program::program_error::ProgramError::InvalidArgument,
                );
            }
            msg!("alt_bn128_identity: success");
            set_return_data(&result);
        }
        _ => {
            msg!("curve-test: unknown opcode {}", instruction_data[0]);
        }
    }

    Ok(())
}
