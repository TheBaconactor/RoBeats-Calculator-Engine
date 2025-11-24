-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
return {
    ["get_price_for_song"] = function(_, p3) --[[ Name: get_price_for_song ]] --[[ Line: 6 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        if v_u_1:singleton():key_get_audiomod(p3) == v_u_1.MOD_HARDMODE then
            return v_u_2.CurrencyType.Stars, 5;
        else
            return v_u_2.CurrencyType.Stars, 1;
        end;
    end
};
