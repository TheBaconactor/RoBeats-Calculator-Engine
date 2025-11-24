-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:04 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict):new()
local v_u_2 = {
    [#v_u_2 + 1] = 515
}
v_u_2[#v_u_2 + 1] = 517
v_u_2[#v_u_2 + 1] = 519
v_u_2[#v_u_2 + 1] = 521
v_u_2[#v_u_2 + 1] = 523
v_u_2[#v_u_2 + 1] = 525
v_u_2[#v_u_2 + 1] = 527
v_u_2[#v_u_2 + 1] = 529
v_u_2[#v_u_2 + 1] = 531
local v3 = {}
for v4 = 1, #v_u_2 do
    v_u_1:add(v_u_2[v4], true)
end;
v3.get_song_select_key_set = function(_) --[[ Name: get_song_select_key_set ]] --[[ Line: 24 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return v_u_1;
end;
v3.get_song_select_table = function(_) --[[ Name: get_song_select_table ]] --[[ Line: 28 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2;
end;
v3.get_tutorial_grant_songkey = function(_) --[[ Name: get_tutorial_grant_songkey ]] --[[ Line: 32 ]]
    return 236;
end;
v3.get_tutorial_play_songkey = function(_) --[[ Name: get_tutorial_play_songkey ]] --[[ Line: 36 ]]
    return 970;
end;
return v3;
