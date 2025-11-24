-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:05 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
local v3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
local v5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v6 = {
    {
        ["Name"] = "RoBeats Top Hits Pack 1",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171193846"
    },
    {
        ["Name"] = "RoBeats Top Hits Pack 2",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171208327"
    },
    {
        ["Name"] = "RoBeats Top Hits Pack 3",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171209347"
    },
    {
        ["Name"] = "Monstercat Song Pack 1",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171209575"
    },
    {
        ["Name"] = "Monstercat Rhythm Game Hits Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171211049"
    },
    {
        ["Name"] = "Fusq Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171211331"
    },
    {
        ["Name"] = "coda Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6527672805"
    },
    {
        ["Name"] = "Creo Song Pack 1",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171219740"
    },
    {
        ["Name"] = "Camellia Song Pack 1",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220049"
    },
    {
        ["Name"] = "Camellia Song Pack 2",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220295"
    },
    {
        ["Name"] = "Hinkik Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220573"
    },
    {
        ["Name"] = "Nash Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171224392"
    },
    {
        ["Name"] = "LeaF Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171224745"
    },
    {
        ["Name"] = "Chroma Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171225199"
    },
    {
        ["Name"] = "RiraN Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171225606"
    },
    {
        ["Name"] = "tv room Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171193846"
    },
    {
        ["Name"] = "Dimrain47 Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171208327"
    },
    {
        ["Name"] = "Seatrus Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171209347"
    },
    {
        ["Name"] = "Kurokotei Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171209575"
    },
    {
        ["Name"] = "Monstercat Song Pack 2",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171211049"
    },
    {
        ["Name"] = "Creo Song Pack 2",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171211331"
    },
    {
        ["Name"] = "BSlick Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6527672805"
    },
    {
        ["Name"] = "Se-U-Ra Song Pack 1",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171219740"
    },
    {
        ["Name"] = "Se-U-Ra Song Pack 2",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220049"
    },
    {
        ["Name"] = "brz1128 Song Pack 2",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220295"
    },
    {
        ["Name"] = "ARForest Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220573"
    },
    {
        ["Name"] = "Silentroom Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171224392"
    },
    {
        ["Name"] = "Emocosine Song Pack 2",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171224745"
    },
    {
        ["Name"] = "Monstercat Song Pack 3",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171225199"
    },
    {
        ["Name"] = "Camellia Song Pack 3",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171225606"
    },
    {
        ["Name"] = "garlagan Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171193846"
    },
    {
        ["Name"] = "naruto2413 Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171225199"
    },
    {
        ["Name"] = "Halloween Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171224745"
    },
    {
        ["Name"] = "xi Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171224392"
    },
    {
        ["Name"] = "James Landino Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220573"
    },
    {
        ["Name"] = "F-777 Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220573"
    },
    {
        ["Name"] = "dark cat Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220573"
    },
    {
        ["Name"] = "Xmas Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220573"
    },
    {
        ["Name"] = "Tobu Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220573"
    },
    {
        ["Name"] = "Slynk Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171193846"
    },
    {
        ["Name"] = "Valentines Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171208327"
    },
    {
        ["Name"] = "Similar Outskirts Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171209347"
    },
    {
        ["Name"] = "MisoilePunch Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171209575"
    },
    {
        ["Name"] = "Waterflame Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171211049"
    },
    {
        ["Name"] = "Hyperpotions Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171211331"
    },
    {
        ["Name"] = "Brz1128 Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6527672805"
    },
    {
        ["Name"] = "Laur Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171219740"
    },
    {
        ["Name"] = "Undead Corporation Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220049"
    },
    {
        ["Name"] = "Maliboux Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220295"
    },
    {
        ["Name"] = "Summer Carnival Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220573"
    },
    {
        ["Name"] = "Team Grimoire Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171224392"
    },
    {
        ["Name"] = "Rutra Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171224745"
    },
    {
        ["Name"] = "Reku Mochizuki Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171225199"
    },
    {
        ["Name"] = "Ardolf Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171225606"
    },
    {
        ["Name"] = "Seatrus Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171193846"
    },
    {
        ["Name"] = "Kobaryo Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171208327"
    },
    {
        ["Name"] = "Sound Space Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171209347"
    },
    {
        ["Name"] = "T+Pazolite Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171209575"
    },
    {
        ["Name"] = "Spring Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171211049"
    },
    {
        ["Name"] = "Chiptune Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171211331"
    },
    {
        ["Name"] = "Hyun Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6527672805"
    },
    {
        ["Name"] = "Summer Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171219740"
    },
    {
        ["Name"] = "Synthion Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220049"
    },
    {
        ["Name"] = "Emocosine Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220295"
    },
    {
        ["Name"] = "Bossfight Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220573"
    },
    {
        ["Name"] = "Autumn Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171224392"
    },
    {
        ["Name"] = "Keisei Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171224745"
    },
    {
        ["Name"] = "Juggernaut Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171225199"
    },
    {
        ["Name"] = "Halv Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171225606"
    },
    {
        ["Name"] = "You Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171193846"
    },
    {
        ["Name"] = "Project Skylate Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171208327"
    },
    {
        ["Name"] = "AAAA Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171209347"
    },
    {
        ["Name"] = "Kagetora Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171209575"
    },
    {
        ["Name"] = "USAO Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171211049"
    },
    {
        ["Name"] = "Nanobii Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171211331"
    },
    {
        ["Name"] = "YooH Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6527672805"
    },
    {
        ["Name"] = "Snail\'s House Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171219740"
    },
    {
        ["Name"] = "Lappy Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220049"
    },
    {
        ["Name"] = "Trance Song Pack",
        ["SongKeys"] = {},
        ["CoverImg"] = "http://www.roblox.com/asset/?id=6171220295"
    }
}
local v7 = v3:new():add_set_from_table_list({
    "http://www.roblox.com/asset/?id=6171193846",
    "http://www.roblox.com/asset/?id=6171208327",
    "http://www.roblox.com/asset/?id=6171209347",
    "http://www.roblox.com/asset/?id=6171209575",
    "http://www.roblox.com/asset/?id=6171211049",
    "http://www.roblox.com/asset/?id=6171211331",
    "http://www.roblox.com/asset/?id=6527672805",
    "http://www.roblox.com/asset/?id=6171219740",
    "http://www.roblox.com/asset/?id=6171220049",
    "http://www.roblox.com/asset/?id=6171220295",
    "http://www.roblox.com/asset/?id=6171220573",
    "http://www.roblox.com/asset/?id=6171224392",
    "http://www.roblox.com/asset/?id=6171224745",
    "http://www.roblox.com/asset/?id=6171225199",
    "http://www.roblox.com/asset/?id=6171225606"
})
local v_u_8 = v3:new()
local v9 = {}
for v10 = 1, #v6 do
    local v11 = v6[v10]
    v_u_2:is_nonempty_string(v11.Name)
    v_u_2:is_nonempty_string(v11.CoverImg)
    v11.Description = "Includes 8 songs total, including normal + hard."
    v_u_2:is_table(v11.SongKeys)
    v_u_2:is_positive(#v11.SongKeys)
    local v12 = v3:new()
    for v13 = 1, #v11.SongKeys do
        local l_SongKeys_0 = v11.SongKeys[v13]
        v_u_2:is_true(v_u_1:singleton():contains_key(l_SongKeys_0))
        v3:set_union(nil, v_u_1:singleton():get_all_modes_of_songkey(l_SongKeys_0), v12)
    end;
    v3:remove_if(v12, function(_, p14) --[[ Line: 1139 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1:singleton():key_get_audiomod(p14) == v_u_1.MOD_EASY;
    end)
    for v15 = 1, #v11.SongKeys do
        local l_SongKeys_1 = v11.SongKeys[v15]
        v_u_2:is_true(v12:contains(l_SongKeys_1), string.format("Sale(%d) Songkey(%d)", v10, l_SongKeys_1))
        local v16 = v_u_1:singleton():key_get_audiomod(l_SongKeys_1)
        v_u_2:is_true(v16 == v_u_1.MOD_NORMAL and true or v16 == v_u_1.MOD_HARDMODE, string.format("Sale(%d) Songkey(%d) AudioMod(%d)", v10, l_SongKeys_1, v16))
        v12:remove(l_SongKeys_1)
    end;
    if v12:count() > 0 then
        warn(v5:table_to_string(v12._table))
    end;
    v_u_2:is_true(v12:count() == 0, string.format("Sale(%d) Extra(%d)", v10, v12:count()))
    v_u_2:is_true(v7:contains(v11.CoverImg), string.format("Sale(%d) CoverImg(%s)", v10, v11.CoverImg))
    v_u_2:is_true(#v11.SongKeys == 8, string.format("Sale(%d) SongKeys(%d)", v10, #v11.SongKeys))
    v_u_8:add(v10, v11)
end;
v5:is_dev_build()
v9.get_songpack_info = function(_) --[[ Name: get_songpack_info ]] --[[ Line: 1181 ]]
    --[[ Upvalues: (copy 1): v_u_8 ]]
    local v17 = {}
    for v18, v19 in v_u_8:key_itr() do
        local l_Limited_0 = v19.Limited
        if l_Limited_0 == nil then
            l_Limited_0 = false
        end;
        v17[#v17 + 1] = {
            ["Name"] = v19.Name,
            ["CoverImg"] = v19.CoverImg,
            ["Description"] = v19.Description,
            ["SaleId"] = v18,
            ["SongKeys"] = v19.SongKeys,
            ["Limited"] = l_Limited_0
        }
    end;
    return v17;
end;
v9.get_title_for_saleid = function(_, p20) --[[ Name: get_title_for_saleid ]] --[[ Line: 1201 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_8 ]]
    v_u_2:is_true(v_u_8:contains(p20))
    return v_u_8:get(p20).Name;
end;
v9.get_songids_for_saleid = function(_, p21) --[[ Name: get_songids_for_saleid ]] --[[ Line: 1206 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_8, (copy 3): v_u_4 ]]
    v_u_2:is_true(v_u_8:contains(p21))
    local v22 = v_u_4:new()
    local l_SongKeys_2 = v_u_8:get(p21).SongKeys
    for v23 = 1, #l_SongKeys_2 do
        v22:push_back(l_SongKeys_2[v23])
    end;
    return v22;
end;
v9.get_purchased_description_for_saleid = function(_, p24) --[[ Name: get_purchased_description_for_saleid ]] --[[ Line: 1216 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_8, (copy 3): v_u_1 ]]
    v_u_2:is_true(v_u_8:contains(p24))
    local v25 = v_u_8:get(p24)
    local l_SongKeys_3 = v25.SongKeys
    local v26 = string.format("Bought \"%s\"! Got %d songs:", v25.Name, #l_SongKeys_3)
    for v27 = 1, #l_SongKeys_3 do
        v26 = v26 .. v_u_1:singleton():get_title_for_key(l_SongKeys_3[v27]) .. ","
    end;
    return v26;
end;
v9.get_shop_image_for_saleid = function(_, p28) --[[ Name: get_shop_image_for_saleid ]] --[[ Line: 1229 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_8 ]]
    v_u_2:is_true(v_u_8:contains(p28))
    return v_u_8:get(p28).CoverImg;
end;
v9.get_shop_description_for_saleid = function(_, p29) --[[ Name: get_shop_description_for_saleid ]] --[[ Line: 1234 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_8 ]]
    v_u_2:is_true(v_u_8:contains(p29))
    return v_u_8:get(p29).Description;
end;
return v9;
