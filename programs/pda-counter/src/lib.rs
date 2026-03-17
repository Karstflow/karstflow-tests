use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint,
    entrypoint::ProgramResult,
    msg,
    program::invoke_signed,
    pubkey::Pubkey,
    system_instruction,
    sysvar::rent::Rent,
    sysvar::Sysvar,
};

entrypoint!(process_instruction);

/// PDA counter: creates a PDA account and stores a u64 counter.
///
/// Instruction 0 (Initialize): create PDA, set counter=0
///   data: [0u8, seed_len: u8, seed: [u8; seed_len]]
///   accounts: [payer(signer,writable), pda(writable), system_program]
///
/// Instruction 1 (Increment): increment counter by 1
///   data: [1u8]
///   accounts: [pda(writable)]
///
/// Instruction 2 (Read): log current counter value
///   data: [2u8]
///   accounts: [pda]
fn process_instruction(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    if instruction_data.is_empty() {
        msg!("pda-counter: empty instruction");
        return Err(solana_program::program_error::ProgramError::InvalidInstructionData);
    }

    match instruction_data[0] {
        0 => initialize(program_id, accounts, instruction_data),
        1 => increment(accounts),
        2 => read_counter(accounts),
        _ => {
            msg!("pda-counter: unknown instruction {}", instruction_data[0]);
            Err(solana_program::program_error::ProgramError::InvalidInstructionData)
        }
    }
}

fn initialize(
    program_id: &Pubkey,
    accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let payer = next_account_info(accounts_iter)?;
    let pda_account = next_account_info(accounts_iter)?;
    let _system_program = next_account_info(accounts_iter)?;

    if instruction_data.len() < 2 {
        return Err(solana_program::program_error::ProgramError::InvalidInstructionData);
    }
    let seed_len = instruction_data[1] as usize;
    if instruction_data.len() < 2 + seed_len {
        return Err(solana_program::program_error::ProgramError::InvalidInstructionData);
    }
    let seed = &instruction_data[2..2 + seed_len];

    let (expected_pda, bump) = Pubkey::find_program_address(&[seed], program_id);
    if expected_pda != *pda_account.key {
        msg!("pda-counter: PDA mismatch");
        return Err(solana_program::program_error::ProgramError::InvalidSeeds);
    }

    let space = 8u64; // u64 counter
    let rent = Rent::get()?;
    let lamports = rent.minimum_balance(space as usize);

    let signer_seeds: &[&[u8]] = &[seed, &[bump]];
    invoke_signed(
        &system_instruction::create_account(payer.key, pda_account.key, lamports, space, program_id),
        &[payer.clone(), pda_account.clone()],
        &[signer_seeds],
    )?;

    // Initialize counter to 0
    let mut data = pda_account.try_borrow_mut_data()?;
    data[..8].copy_from_slice(&0u64.to_le_bytes());

    msg!("pda-counter: initialized at {} bump={}", pda_account.key, bump);
    Ok(())
}

fn increment(accounts: &[AccountInfo]) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let pda_account = next_account_info(accounts_iter)?;

    let mut data = pda_account.try_borrow_mut_data()?;
    let mut counter = u64::from_le_bytes(data[..8].try_into().unwrap());
    counter += 1;
    data[..8].copy_from_slice(&counter.to_le_bytes());

    msg!("pda-counter: incremented to {}", counter);
    Ok(())
}

fn read_counter(accounts: &[AccountInfo]) -> ProgramResult {
    let accounts_iter = &mut accounts.iter();
    let pda_account = next_account_info(accounts_iter)?;

    let data = pda_account.try_borrow_data()?;
    let counter = u64::from_le_bytes(data[..8].try_into().unwrap());

    msg!("pda-counter: value={}", counter);
    Ok(())
}
