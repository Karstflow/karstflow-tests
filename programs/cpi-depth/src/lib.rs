use solana_program::{
    account_info::AccountInfo,
    entrypoint,
    entrypoint::ProgramResult,
    instruction::{AccountMeta, Instruction},
    msg,
    program::invoke,
    program::set_return_data,
    pubkey::Pubkey,
};

entrypoint!(process_instruction);

/// CPI depth test program.
///
/// Reads depth from instruction_data[0].
/// If depth > 0: invokes self with depth-1 via CPI.
/// At depth 0: sets return_data("bottom") and logs.
///
/// This tests CPI call depth limits (Solana limit = 4 levels).
fn process_instruction(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    let depth = if instruction_data.is_empty() {
        0u8
    } else {
        instruction_data[0]
    };

    msg!("cpi-depth: depth={}", depth);

    if depth == 0 {
        msg!("cpi-depth: reached bottom");
        set_return_data(b"bottom");
        return Ok(());
    }

    // Build CPI to self with depth-1
    let new_data = vec![depth - 1];
    let account_metas: Vec<AccountMeta> = accounts
        .iter()
        .map(|a| {
            if a.is_writable {
                AccountMeta::new(*a.key, a.is_signer)
            } else {
                AccountMeta::new_readonly(*a.key, a.is_signer)
            }
        })
        .collect();

    let ix = Instruction::new_with_bytes(*program_id, &new_data, account_metas);

    invoke(&ix, accounts)?;

    msg!("cpi-depth: returned from depth={}", depth - 1);
    Ok(())
}
