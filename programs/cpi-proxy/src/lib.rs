use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint,
    entrypoint::ProgramResult,
    msg,
    program::invoke,
    pubkey::Pubkey,
    system_instruction,
};

entrypoint!(process_instruction);

/// CPI proxy: transfers lamports from source to destination via System Program.
///
/// Instruction data: 8 bytes (u64 LE) = amount in lamports
///
/// Accounts:
///   0. `[signer, writable]` source (payer)
///   1. `[writable]` destination
///   2. `[]` system program
fn process_instruction(
    _program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let source = next_account_info(accounts_iter)?;
    let destination = next_account_info(accounts_iter)?;
    let _system_program = next_account_info(accounts_iter)?;

    if instruction_data.len() < 8 {
        msg!("cpi-proxy: need 8 bytes for amount");
        return Err(solana_program::program_error::ProgramError::InvalidInstructionData);
    }

    let amount = u64::from_le_bytes(instruction_data[..8].try_into().unwrap());
    msg!(
        "cpi-proxy: transfer {} lamports from {} to {}",
        amount,
        source.key,
        destination.key
    );

    let ix = system_instruction::transfer(source.key, destination.key, amount);
    invoke(&ix, &[source.clone(), destination.clone()])?;

    msg!("cpi-proxy: transfer complete");
    Ok(())
}
