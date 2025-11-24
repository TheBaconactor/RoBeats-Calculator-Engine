-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:46 PM
-- Cached decompilation

local v1 = {}
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict):new():add_set_from_table_list({
    405,
    406,
    45,
    212,
    495,
    496,
    1175,
    1176,
    1177,
    1252,
    1253,
    1254,
    1255,
    1256,
    1257,
    1258,
    1259,
    1260,
    1320,
    1321,
    1322,
    1324,
    1325,
    1326,
    1327,
    1361,
    1362,
    1363,
    1364,
    1365,
    1366,
    1367,
    1368,
    1369,
    1370,
    1504,
    1505,
    1511,
    1512,
    1513,
    1516,
    1517,
    1657,
    1658,
    1861,
    1862
})
v1.songkey_has_special_info_text = function(_, p3) --[[ Name: songkey_has_special_info_text ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    if v_u_2:contains(p3) then
        return true, "\194\169Team Shanghai Alice";
    else
        return false, "";
    end;
end;
return v1;
