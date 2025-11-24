-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:45 PM
-- Time elapsed: 11 milliseconds

local v1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = v1:new()
local v_u_3 = v1:new()
local v4 = {}
for v5, v6 in pairs({
    ["AAAA"] = "rbxassetid://17737244481",
    ["Ardolf"] = "rbxassetid://10395956917",
    ["Atsuover"] = "rbxassetid://8511327738",
    ["ARForest"] = "rbxassetid://7423377548",
    ["BlackY"] = "rbxassetid://135389402989179",
    ["Bossfight"] = "rbxassetid://14696219728",
    ["brz1128"] = "rbxassetid://9307113883",
    ["BSlick"] = "rbxassetid://10395957132",
    ["Camellia"] = "http://www.roblox.com/asset/?id=7449969763",
    ["Chroma"] = "rbxassetid://7423377242",
    ["coda"] = "rbxassetid://10395957311",
    ["Creo"] = "http://www.roblox.com/asset/?id=7739768148",
    ["dark cat"] = "rbxassetid://8201687202",
    ["Dimrain47"] = "rbxassetid://10395957593",
    ["Egg Yolk"] = "rbxassetid://10395957823",
    ["F-777"] = "rbxassetid://8037221347",
    ["FinnMK"] = "rbxassetid://10395960238",
    ["fusq"] = "rbxassetid://124083396965248",
    ["EmoCosine"] = "http://www.roblox.com/asset/?id=14305911527",
    ["garlagan"] = "http://www.roblox.com/asset/?id=7547707871",
    ["Geoxor"] = "rbxassetid://9850868387",
    ["HalfDuck"] = "rbxassetid://132146960780538",
    ["Halv"] = "rbxassetid://16457192462",
    ["Haywyre"] = "rbxassetid://10395958319",
    ["Hinkik"] = "rbxassetid://10395960428",
    ["HyuN"] = "rbxassetid://13189761830",
    ["Hyper Potions"] = "rbxassetid://9181110093",
    ["James Landino"] = "rbxassetid://7962389205",
    ["Juggernaut"] = "rbxassetid://15875586407",
    ["Just Dance"] = "rbxassetid://8076636270",
    ["Kagetora"] = "rbxassetid://18524512790",
    ["Kagi"] = "rbxassetid://138744048510598",
    ["Kanro"] = "rbxassetid://13481743636",
    ["Kawai Sprite"] = "http://www.roblox.com/asset/?id=7449656847",
    ["keisei"] = "rbxassetid://15099939834",
    ["KepoWorld"] = "rbxassetid://8581932683",
    ["Kobaryo"] = "rbxassetid://11638645841",
    ["Kurokotei"] = "rbxassetid://9371413433",
    ["Laur [LAUR1200]"] = "rbxassetid://9432001124",
    ["Lappy"] = "rbxassetid://73951460269568",
    ["LeaF (7eaF)"] = "rbxassetid://9106287951",
    ["Make a Cake"] = "rbxassetid://11734690582",
    ["Maliboux"] = "rbxassetid://9985788282",
    ["matthieumusic"] = "rbxassetid://10395958726",
    ["MisoilePunch"] = "rbxassetid://8919429427",
    ["Monstercat"] = "rbxassetid://7423376285",
    ["nanobii"] = "rbxassetid://125565568920226",
    ["Nash Music Library"] = "rbxassetid://10395958945",
    ["naruto2413"] = "http://www.roblox.com/asset/?id=7676766574",
    ["nekodex"] = "rbxassetid://10395959108",
    ["NOMA"] = "rbxassetid://10078813121",
    ["Project Skylate"] = "rbxassetid://17440162252",
    ["Reku Mochizuki"] = "rbxassetid://10969991958",
    ["RiraN"] = "rbxassetid://9712478845",
    ["Rousseau"] = "rbxassetid://10395959311",
    ["Rutra"] = "rbxassetid://10395959471",
    ["seatrus"] = "rbxassetid://11323211868",
    ["Se-U-Ra"] = "rbxassetid://8186575425",
    ["Silentroom"] = "rbxassetid://7423375746",
    ["Similar Outskirts"] = "rbxassetid://8837883643",
    ["Slynk"] = "rbxassetid://8644542054",
    ["Sound Space"] = "rbxassetid://12100501047",
    ["Synthion"] = "rbxassetid://13763581877",
    ["Team Grimoire"] = "rbxassetid://10358939485",
    ["Tobu"] = "rbxassetid://8401605626",
    ["tv room"] = "rbxassetid://10395959601",
    ["t+pazolite"] = "rbxassetid://11389352283",
    ["Snail\'s House"] = "rbxassetid://93065950225614",
    ["UNDEAD CORPORATION"] = "rbxassetid://9673170317",
    ["USAO"] = "rbxassetid://18963805981",
    ["Waterflame"] = "http://www.roblox.com/asset/?id=9082984815",
    ["xi (xi_com_giko_31)"] = "rbxassetid://7903066620",
    ["YooH"] = "rbxassetid://74689269460765",
    ["you"] = "rbxassetid://17087355770"
}) do
    v_u_2:add_set(v5)
    v_u_3:add(v5, v6)
end;
v4.get_set = function(_) --[[ Name: get_set ]] --[[ Line: 89 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2;
end;
v4.artist_name_to_icon = function(_, p7) --[[ Name: artist_name_to_icon ]] --[[ Line: 93 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    local v8 = v_u_3:get(p7)
    return v8 == nil and "" or v8;
end;
local v_u_9 = v1:new()
v4.artist_name_is_selectable = function(_, p10) --[[ Name: artist_name_is_selectable ]] --[[ Line: 100 ]]
    --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_2 ]]
    if v_u_9:contains(p10) then
        local v11 = v_u_9:get(p10)
        return v11 ~= false, v11;
    end;
    if v_u_2:contains(p10) then
        v_u_9:add(p10, p10)
        return true, p10;
    end;
    local v12 = string.lower(p10)
    for v13, _ in v_u_2:key_itr() do
        if string.find(v12, string.lower(v13), 1, true) ~= nil then
            v_u_9:add(p10, v13)
            return true, v13;
        end;
    end;
    v_u_9:add(p10, false)
    return false, "";
end;
return v4;
